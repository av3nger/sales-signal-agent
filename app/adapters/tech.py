"""Tech adapter for technology adoption and migration signals."""

from typing import Optional

from app.schemas import CompanyInput, ICPInput, SourceType

from .base import BaseAdapter


class TechAdapter(BaseAdapter):
    """Adapter for searching technology adoption and tool changes."""

    source_type = SourceType.NEWS
    adapter_name = "tech"

    def get_queries(self, company: CompanyInput, icp: Optional[ICPInput] = None) -> list[str]:
        """Generate queries focused on technology adoption and migrations.

        If ICP is provided, focuses on ICP-relevant technology changes.
        """
        name = company.name

        # Base queries
        queries = [
            # Technology adoption
            f'"{name}" adopts implements new technology',
            f'"{name}" technology stack modernization',
            f'"{name}" SaaS cloud adoption',
            # Migrations
            f'"{name}" migrates migration cloud',
            f'"{name}" digital transformation',
            f'"{name}" platform switch new system',
        ]

        # If ICP provided, add ICP-specific tech queries
        if icp:
            keyword_str = " ".join(icp.keywords[:3])
            queries.extend([
                f'"{name}" {keyword_str} technology adoption',
                f'"{name}" {keyword_str} platform tools',
                f'"{name}" implements {keyword_str} solution',
            ])
            if icp.description:
                queries.append(f'"{name}" {icp.description} technology')
        else:
            # Default: common tech investments
            queries.extend([
                f'"{name}" AI machine learning implementation',
                f'"{name}" cybersecurity tools security platform',
            ])

        # Add industry-specific queries if available
        if company.industry:
            queries.append(f'"{name}" {company.industry} technology investment')

        return queries
