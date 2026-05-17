"""Jobs adapter for hiring activity and job opening signals."""

from typing import Optional

from app.schemas import CompanyInput, ICPInput, SourceType

from .base import BaseAdapter


class JobsAdapter(BaseAdapter):
    """Adapter for searching job openings and hiring activity."""

    source_type = SourceType.NEWS
    adapter_name = "jobs"

    def get_queries(self, company: CompanyInput, icp: Optional[ICPInput] = None) -> list[str]:
        """Generate queries focused on job openings and hiring activity.

        If ICP is provided, focuses on ICP-relevant job postings.
        """
        name = company.name

        # Base queries
        queries = [
            # General hiring activity
            f'"{name}" careers hiring open positions',
            f'"{name}" job openings employment opportunities',
            f'"{name}" talent acquisition recruiting',
        ]

        # If ICP provided, focus on ICP-specific roles
        if icp:
            keyword_str = " OR ".join(icp.keywords)
            queries.extend([
                f'"{name}" hiring {keyword_str}',
                f'"{name}" job opening {keyword_str}',
                f'"{name}" recruiting {keyword_str}',
            ])
            if icp.description:
                queries.append(f'"{name}" careers {icp.description}')
        else:
            # Default: generic role categories
            queries.extend([
                f'"{name}" hiring engineers developers',
                f'"{name}" hiring sales marketing',
            ])

        # Expansion indicators
        queries.extend([
            f'"{name}" growing team expanding workforce',
            f'"{name}" new office hiring spree',
        ])

        # Add industry-specific queries if available
        if company.industry:
            queries.append(f'"{name}" {company.industry} hiring jobs')

        return queries
