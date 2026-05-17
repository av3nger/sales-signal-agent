"""News adapter for executive movement signals."""

from typing import Optional

from app.schemas import CompanyInput, ICPInput, SourceType

from .base import BaseAdapter


class NewsAdapter(BaseAdapter):
    """Adapter for searching news about executive movements and compliance hires."""

    source_type = SourceType.NEWS
    adapter_name = "news"

    # Default keywords when no ICP is provided
    DEFAULT_KEYWORDS = ["compliance", "risk", "security"]

    def get_queries(self, company: CompanyInput, icp: Optional[ICPInput] = None) -> list[str]:
        """Generate queries focused on executive hires and leadership.

        If ICP is provided, uses ICP keywords instead of default compliance/risk/security focus.
        """
        name = company.name

        # Use ICP keywords or defaults
        keywords = icp.keywords if icp else self.DEFAULT_KEYWORDS
        keyword_str = " OR ".join(keywords)

        queries = [
            f'"{name}" appointed Chief {keyword_str}',
            f'"{name}" hires Head of {keyword_str}',
            f'"{name}" new VP {keyword_str}',
            f'"{name}" executive appointment {keyword_str}',
        ]

        # Add ICP description as a query if provided
        if icp and icp.description:
            queries.append(f'"{name}" {icp.description} leadership')

        # Add industry-specific queries if available
        if company.industry:
            queries.append(f'"{name}" {company.industry} leadership change')

        return queries
