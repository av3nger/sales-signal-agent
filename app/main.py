"""FastAPI application for Sales Signal Research Agent."""

import asyncio
import time
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from app.adapters import (
    BudgetAdapter,
    FinancialAdapter,
    JobsAdapter,
    NewsAdapter,
    RegulatoryAdapter,
    TechAdapter,
)
from app.adapters.base import BaseAdapter
from app.extractor import EventExtractor
from app.logging_config import get_logger, setup_logging
from app.schemas import (
    CompanyInput,
    EvidenceItem,
    EvidenceWithEvent,
    ICPInput,
    SignalRequest,
    SignalResponse,
    SignalType,
    SingleSignalRequest,
    SingleSignalResponse,
)
from app.signal_engine import SignalEngine

# Initialize logging
setup_logging()
logger = get_logger("main")

app = FastAPI(
    title="Sales Signal Research Agent",
    description="API for researching sales signals based on public web data",
    version="0.1.0",
)

# Signal type to adapter mapping
SIGNAL_TYPE_ADAPTERS: dict[SignalType, type[BaseAdapter]] = {
    SignalType.EXEC_MOVEMENT: NewsAdapter,
    SignalType.REGULATORY_PRESSURE: RegulatoryAdapter,
    SignalType.FINANCIAL_TRENDS: FinancialAdapter,
    SignalType.JOB_OPENINGS: JobsAdapter,
    SignalType.TECH_TOOL_CHANGES: TechAdapter,
    SignalType.BUDGET_TRENDS: BudgetAdapter,
}


async def collect_evidence(
    company: CompanyInput,
    adapters: list[BaseAdapter],
    icp: ICPInput | None = None,
) -> list[EvidenceItem]:
    """Collect evidence from specified adapters concurrently.

    Args:
        company: Company to search for.
        adapters: List of adapter instances to use.
        icp: Optional ICP to customize search queries.

    Returns:
        List of collected evidence items.
    """
    if icp:
        logger.info(f"Collecting evidence with ICP: {icp.keywords}")
    logger.info(f"Collecting evidence from {len(adapters)} adapter(s)...")

    try:
        evidence_results = await asyncio.gather(
            *[adapter.search(company, icp) for adapter in adapters],
            return_exceptions=True,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error collecting evidence: {str(e)}",
        )

    # Flatten and filter out exceptions
    all_evidence: list[EvidenceItem] = []
    for result in evidence_results:
        if isinstance(result, list):
            all_evidence.extend(result)
        elif isinstance(result, Exception):
            logger.warning(f"Adapter error: {result}")

    logger.info(
        f"Evidence collection complete: {len(all_evidence)} items from {len(adapters)} adapter(s)"
    )

    return all_evidence


async def extract_and_compute(
    evidence: list[EvidenceItem],
    company_name: str,
    signal_types: list[SignalType] | None = None,
    icp: ICPInput | None = None,
) -> tuple[list[EvidenceWithEvent], SignalEngine]:
    """Extract events from evidence and prepare signal engine.

    Args:
        evidence: List of evidence items.
        company_name: Company name for context.
        signal_types: Optional filter for specific signal types.
        icp: Optional ICP to provide context for extraction.

    Returns:
        Tuple of (evidence with events, signal engine instance).
    """
    if not evidence:
        return [], SignalEngine(icp=icp)

    # Extract events from evidence using LLM
    extractor = EventExtractor()
    try:
        evidence_with_events = await extractor.extract_all(evidence, company_name, icp)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error extracting events: {str(e)}",
        )

    return evidence_with_events, SignalEngine(icp=icp)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/analyze", response_model=SignalResponse)
async def analyze_company(request: SignalRequest) -> SignalResponse:
    """
    Analyze a company for sales signals.

    Collects evidence from multiple sources, extracts structured events,
    and computes signals for:
    - EXEC_MOVEMENT: Leadership changes in compliance/risk/security
    - REGULATORY_PRESSURE: Fines, audits, compliance deadlines
    - FINANCIAL_TRENDS: Funding, layoffs, revenue changes
    - JOB_OPENINGS: Hiring activity, open positions
    - TECH_TOOL_CHANGES: Technology adoption, migrations
    - BUDGET_TRENDS: Budget allocation, spending changes
    """
    start_time = time.time()
    company = request.company
    icp = request.icp

    logger.info(f"Starting analysis for company: {company.name} ({company.domain})")
    if icp:
        logger.info(f"Using ICP filter: {icp.keywords}")

    # Determine which adapters to use based on signal_types filter
    if request.signal_types:
        adapter_classes = [
            SIGNAL_TYPE_ADAPTERS[st]
            for st in request.signal_types
            if st in SIGNAL_TYPE_ADAPTERS
        ]
        adapters = [cls() for cls in adapter_classes]
        if not adapters:
            raise HTTPException(
                status_code=400,
                detail=f"No valid signal types provided. Valid types: {list(SignalType)}",
            )
    else:
        # Use all adapters
        adapters = [
            NewsAdapter(),
            RegulatoryAdapter(),
            FinancialAdapter(),
            JobsAdapter(),
            TechAdapter(),
            BudgetAdapter(),
        ]

    # Collect evidence
    all_evidence = await collect_evidence(company, adapters, icp)

    if not all_evidence:
        # Return neutral response if no evidence found
        logger.info("No evidence found, returning neutral response")
        signal_engine = SignalEngine(icp=icp)
        signals = signal_engine.compute_signals([])

        # Filter signals if specific types requested
        if request.signal_types:
            signals = [s for s in signals if s.type in request.signal_types]

        recommendation, reasons = signal_engine.compute_recommendation(signals)

        duration = time.time() - start_time
        logger.info(
            f"Analysis complete in {duration:.1f}s - Recommendation: {recommendation.value}"
        )

        return SignalResponse(
            company_domain=company.domain,
            analyzed_at=datetime.now(timezone.utc),
            signals=signals,
            recommendation=recommendation,
            recommendation_reasons=reasons,
        )

    # Extract events and compute signals
    logger.info("Extracting events from evidence...")
    evidence_with_events, signal_engine = await extract_and_compute(
        all_evidence, company.name, request.signal_types, icp
    )

    logger.info("Computing signals...")
    signals = signal_engine.compute_signals(evidence_with_events)

    # Filter signals if specific types requested
    if request.signal_types:
        signals = [s for s in signals if s.type in request.signal_types]

    # Compute recommendation
    recommendation, reasons = signal_engine.compute_recommendation(signals)

    duration = time.time() - start_time
    logger.info(
        f"Analysis complete in {duration:.1f}s - Recommendation: {recommendation.value}"
    )

    return SignalResponse(
        company_domain=company.domain,
        analyzed_at=datetime.now(timezone.utc),
        signals=signals,
        recommendation=recommendation,
        recommendation_reasons=reasons,
    )


@app.post("/analyze/{signal_type}", response_model=SingleSignalResponse)
async def analyze_single_signal(
    signal_type: SignalType, request: SingleSignalRequest
) -> SingleSignalResponse:
    """
    Analyze a company for a specific signal type.

    Available signal types:
    - EXEC_MOVEMENT: Leadership changes in compliance/risk/security
    - REGULATORY_PRESSURE: Fines, audits, compliance deadlines
    - FINANCIAL_TRENDS: Funding, layoffs, revenue changes
    - JOB_OPENINGS: Hiring activity, open positions
    - TECH_TOOL_CHANGES: Technology adoption, migrations
    - BUDGET_TRENDS: Budget allocation, spending changes
    """
    start_time = time.time()
    company = request.company
    icp = request.icp

    logger.info(
        f"Starting {signal_type.value} analysis for company: {company.name} ({company.domain})"
    )
    if icp:
        logger.info(f"Using ICP filter: {icp.keywords}")

    # Get the appropriate adapter for this signal type
    adapter_class = SIGNAL_TYPE_ADAPTERS.get(signal_type)
    if not adapter_class:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown signal type: {signal_type}. Valid types: {list(SignalType)}",
        )

    adapter = adapter_class()

    # Collect evidence from single adapter
    all_evidence = await collect_evidence(company, [adapter], icp)

    # Extract events and compute signal
    evidence_with_events, signal_engine = await extract_and_compute(
        all_evidence, company.name, [signal_type], icp
    )

    logger.info(f"Computing {signal_type.value} signal...")
    signal = signal_engine.compute_single_signal(evidence_with_events, signal_type)

    duration = time.time() - start_time
    logger.info(
        f"{signal_type.value} analysis complete in {duration:.1f}s - Status: {signal.status.value}"
    )

    return SingleSignalResponse(
        company_domain=company.domain,
        analyzed_at=datetime.now(timezone.utc),
        signal=signal,
    )
