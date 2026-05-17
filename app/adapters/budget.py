"""Budget adapter for budget allocation and spending signals."""

from typing import Optional

from app.schemas import CompanyInput, ICPInput, SourceType

from .base import BaseAdapter


class BudgetAdapter(BaseAdapter):
    """Adapter for searching budget allocation and spending trends."""

    source_type = SourceType.FINANCIAL
    adapter_name = "budget"

    def get_queries(self, company: CompanyInput, icp: Optional[ICPInput] = None) -> list[str]:
        """Generate queries focused on budget and spending trends.

        If ICP is provided, focuses on ICP-relevant budget areas.
        """
        name = company.name

        # Base queries
        queries = [
            # Budget allocation
            f'"{name}" budget allocation spending',
            f'"{name}" investment spending increase',
            # Cost changes
            f'"{name}" cost reduction cuts',
            f'"{name}" capex capital expenditure',
            # Financial planning
            f'"{name}" budget planning fiscal year',
            f'"{name}" spending freeze budget constraints',
        ]

        # If ICP provided, add ICP-specific budget queries
        if icp:
            keyword_str = " ".join(icp.keywords[:3])
            queries.extend([
                f'"{name}" {keyword_str} budget spending',
                f'"{name}" {keyword_str} investment allocation',
            ])
            if icp.description:
                queries.append(f'"{name}" {icp.description} budget')
        else:
            # Default: common budget areas
            queries.extend([
                f'"{name}" IT budget technology spending',
                f'"{name}" R&D investment research development',
            ])

        # Add industry-specific queries if available
        if company.industry:
            queries.append(f'"{name}" {company.industry} budget investment')

        return queries
