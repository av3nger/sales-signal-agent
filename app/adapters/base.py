"""Base adapter interface for evidence collection."""

from abc import ABC, abstractmethod
from typing import Optional

from tavily import AsyncTavilyClient

from app.config import get_settings
from app.logging_config import get_logger
from app.schemas import CompanyInput, EvidenceItem, ICPInput, SourceType


class BaseAdapter(ABC):
    """Base class for evidence adapters."""

    source_type: SourceType
    adapter_name: str = "base"

    def __init__(self) -> None:
        settings = get_settings()
        self.tavily_client = AsyncTavilyClient(api_key=settings.tavily_api_key)
        self.max_results = settings.max_evidence_per_adapter
        self.logger = get_logger(self.adapter_name)

    @abstractmethod
    def get_queries(self, company: CompanyInput, icp: Optional[ICPInput] = None) -> list[str]:
        """Generate search queries for the company.

        Args:
            company: Company to search for.
            icp: Optional Ideal Customer Profile to customize queries.
        """
        pass

    async def search(self, company: CompanyInput, icp: Optional[ICPInput] = None) -> list[EvidenceItem]:
        """Execute search and return evidence items."""
        queries = self.get_queries(company, icp)
        all_evidence: list[EvidenceItem] = []

        self.logger.info(f"Executing {len(queries)} queries for {company.name}")

        for idx, query in enumerate(queries, 1):
            try:
                response = await self.tavily_client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=5,
                    include_raw_content=True,
                )

                results = response.get("results", [])
                result_count = len(results)
                # Truncate query for display (first 50 chars)
                query_display = query[:50] + "..." if len(query) > 50 else query
                self.logger.info(f"Query {idx}/{len(queries)}: {query_display} - {result_count} results")

                for result in results:
                    evidence = EvidenceItem(
                        source_type=self.source_type,
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        published_at=result.get("published_date"),
                        snippet=result.get("content", "")[:500],
                        raw_content=result.get("raw_content", "")[:2000] if result.get("raw_content") else None,
                    )
                    all_evidence.append(evidence)

            except Exception as e:
                self.logger.warning(f"Error on query {idx}/{len(queries)}: {e}")
                continue

        # Deduplicate by URL
        seen_urls: set[str] = set()
        unique_evidence: list[EvidenceItem] = []
        for item in all_evidence:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_evidence.append(item)

        result = unique_evidence[: self.max_results]
        self.logger.info(f"Completed: {len(result)} evidence items collected")

        return result
