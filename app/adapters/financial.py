"""Financial adapter for funding, layoffs, and financial trend signals."""

from typing import Optional

from app.schemas import CompanyInput, ICPInput, SourceType

from .base import BaseAdapter


class FinancialAdapter(BaseAdapter):
    """Adapter for searching financial events: funding, layoffs, revenue, M&A."""

    source_type = SourceType.FINANCIAL
    adapter_name = "financial"

    def get_queries(self, company: CompanyInput, icp: Optional[ICPInput] = None) -> list[str]:
        """Generate queries focused on financial events and trends.

        If ICP is provided, adds ICP-specific financial queries.
        """
        name = company.name

        queries = [
            # Funding and investment
            f'"{name}" funding round series investment raised',
            f'"{name}" venture capital private equity investment',
            # Layoffs and workforce changes
            f'"{name}" layoffs workforce reduction hiring freeze',
            f'"{name}" job cuts restructuring downsizing',
            # Revenue and growth
            f'"{name}" revenue growth quarterly results earnings',
            f'"{name}" expansion new market growth',
            # M&A and budget
            f'"{name}" acquisition merger acquired',
            f'"{name}" budget cut cost reduction spending',
        ]

        # Add industry context if available
        if company.industry:
            queries.append(f'"{name}" {company.industry} financial performance')

        # Add ICP-specific financial queries
        if icp:
            keyword_str = " ".join(icp.keywords[:3])
            queries.append(f'"{name}" {keyword_str} investment spending')
            if icp.description:
                queries.append(f'"{name}" {icp.description} budget')

        return queries
