"""LLM-based event extraction from evidence."""

import json
from typing import Optional

import anthropic

from app.config import get_settings
from app.logging_config import get_logger
from app.schemas import (
    EvidenceItem,
    EvidenceWithEvent,
    EventType,
    ExtractedEvent,
    FinancialSubtype,
    ICPInput,
)

logger = get_logger("extractor")

EXTRACTION_PROMPT = """You are an expert at extracting structured business events from news articles and documents.

Analyze the following text and extract the most relevant business event. Focus on:
1. Executive hires/departures (especially in compliance, risk, security roles)
2. Regulatory actions (fines, audits, enforcement, deadlines)
3. Financial events (funding, layoffs, revenue changes, M&A, budget cuts)
4. Job openings and hiring activity (careers, open positions, talent acquisition)
5. Technology tool changes (adopts, implements, migrates, technology stack, SaaS, cloud)
6. Budget trends (budget allocation, spending changes, investment, cost reduction, capex)

Return a JSON object with these fields:
- event_type: One of "EXEC_HIRE", "EXEC_DEPARTURE", "REGULATORY_ACTION", "REGULATORY_DEADLINE", "FINANCIAL_EVENT", "JOB_POSTING", "TECH_ADOPTION", "TECH_MIGRATION", "BUDGET_CHANGE", "OTHER"
- financial_subtype: If event_type is "FINANCIAL_EVENT", one of "FUNDING", "LAYOFF", "REVENUE_CHANGE", "ACQUISITION", "BUDGET_CUT", "EXPANSION", "HIRING". Otherwise null.
- entity_name: Name of person or organization involved (if applicable)
- role: Job title/role if this is an executive movement (if applicable)
- seniority: One of "C-LEVEL", "VP", "DIRECTOR", "MANAGER" (if applicable)
- event_date: Date of event in YYYY-MM-DD format (if mentioned)
- amount: Dollar amount if applicable (e.g., "$10M", "$5.2B")
- regulator: Name of regulatory body if applicable (e.g., "SEC", "FCA", "ASIC")
- summary: Brief 1-sentence summary of the event
- relevance_score: Float 0.0-1.0 indicating how relevant this is for sales signal detection

IMPORTANT:
- Return ONLY valid JSON, no markdown or explanation
- If the text doesn't contain a clear business event, set event_type to "OTHER" and relevance_score to 0.1
- Be precise about dates and amounts
- For seniority: CEO/CFO/CRO/CISO/CTO = C-LEVEL, VP/SVP/EVP = VP, Director = DIRECTOR, Manager/Head = MANAGER

Text to analyze:
{text}

Company context: {company_name}
{icp_context}
JSON response:"""


class EventExtractor:
    """Extracts structured events from evidence using Claude."""

    def __init__(self) -> None:
        settings = get_settings()
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.llm_model
        self.max_tokens = settings.llm_max_tokens

    async def extract_event(
        self, evidence: EvidenceItem, company_name: str, icp: Optional[ICPInput] = None
    ) -> Optional[ExtractedEvent]:
        """Extract a structured event from evidence text."""
        # Use raw_content if available, otherwise fall back to snippet
        text = evidence.raw_content or evidence.snippet
        if not text or len(text.strip()) < 50:
            return None

        # Build ICP context if provided
        icp_context = ""
        if icp:
            icp_context = f"\nIdeal Customer Profile focus: {', '.join(icp.keywords)}"
            if icp.description:
                icp_context += f"\nICP Description: {icp.description}"
            icp_context += "\nPrioritize events related to these areas when calculating relevance_score."

        prompt = EXTRACTION_PROMPT.format(
            text=text[:2000], company_name=company_name, icp_context=icp_context
        )

        try:
            # Note: Using sync client in async context for simplicity
            # In production, use anthropic.AsyncAnthropic
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text.strip()

            # Clean up response if it has markdown code blocks
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            event_data = json.loads(content)

            # Validate and create ExtractedEvent
            event = ExtractedEvent(
                event_type=EventType(event_data.get("event_type", "OTHER")),
                financial_subtype=(
                    FinancialSubtype(event_data["financial_subtype"])
                    if event_data.get("financial_subtype")
                    else None
                ),
                entity_name=event_data.get("entity_name"),
                role=event_data.get("role"),
                seniority=event_data.get("seniority"),
                event_date=event_data.get("event_date"),
                amount=event_data.get("amount"),
                regulator=event_data.get("regulator"),
                summary=event_data.get("summary", "Event detected"),
                relevance_score=float(event_data.get("relevance_score", 0.5)),
            )

            return event

        except json.JSONDecodeError:
            # Retry once with a simpler prompt
            return await self._retry_extraction(text, company_name)
        except Exception as e:
            print(f"Extraction error: {e}")
            return None

    async def _retry_extraction(
        self, text: str, company_name: str
    ) -> Optional[ExtractedEvent]:
        """Simplified retry on JSON parse failure."""
        simple_prompt = f"""Extract the main business event from this text about {company_name}.
Return ONLY a JSON object with: event_type, summary, relevance_score.
event_type must be one of: EXEC_HIRE, EXEC_DEPARTURE, REGULATORY_ACTION, REGULATORY_DEADLINE, FINANCIAL_EVENT, JOB_POSTING, TECH_ADOPTION, TECH_MIGRATION, BUDGET_CHANGE, OTHER

Text: {text[:1000]}

JSON:"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=256,
                messages=[{"role": "user", "content": simple_prompt}],
            )

            content = response.content[0].text.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
                content = content.strip()

            event_data = json.loads(content)

            return ExtractedEvent(
                event_type=EventType(event_data.get("event_type", "OTHER")),
                summary=event_data.get("summary", "Event detected"),
                relevance_score=float(event_data.get("relevance_score", 0.3)),
            )
        except Exception:
            return None

    async def extract_all(
        self, evidence_items: list[EvidenceItem], company_name: str, icp: Optional[ICPInput] = None
    ) -> list[EvidenceWithEvent]:
        """Extract events from all evidence items."""
        results: list[EvidenceWithEvent] = []
        total = len(evidence_items)

        logger.info(f"Extracting events from {total} evidence items...")
        if icp:
            logger.info(f"Using ICP context: {icp.keywords}")

        for idx, item in enumerate(evidence_items, 1):
            event = await self.extract_event(item, company_name, icp)
            results.append(EvidenceWithEvent(evidence=item, event=event))
            logger.info(f"Extracted {idx}/{total}")

        logger.info(f"Extraction complete: {total} items processed")

        return results
