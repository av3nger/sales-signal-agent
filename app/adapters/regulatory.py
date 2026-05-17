"""Regulatory adapter for compliance pressure signals."""

from typing import Optional

from app.schemas import CompanyInput, ICPInput, SourceType

from .base import BaseAdapter


class RegulatoryAdapter(BaseAdapter):
    """Adapter for searching regulatory actions, fines, and compliance deadlines."""

    source_type = SourceType.REGULATORY
    adapter_name = "regulatory"

    def get_queries(self, company: CompanyInput, icp: Optional[ICPInput] = None) -> list[str]:
        """Generate queries focused on regulatory actions and compliance pressure.

        If ICP is provided, adds ICP-specific regulatory queries.
        """
        name = company.name

        # Base regulatory queries
        queries = [
            f'"{name}" fine penalty enforcement action',
            f'"{name}" regulatory audit investigation',
            f'"{name}" compliance violation breach',
            f'"{name}" consent order settlement',
        ]

        # Add country-specific regulator queries
        country = company.country or ""
        if country.upper() == "AU":
            queries.extend(
                [
                    f'"{name}" ASIC APRA enforcement',
                    f'"{name}" ACCC investigation',
                ]
            )
        elif country.upper() == "US":
            queries.extend(
                [
                    f'"{name}" SEC enforcement action',
                    f'"{name}" FTC CFPB investigation',
                    f'"{name}" DOJ settlement',
                ]
            )
        elif country.upper() == "UK":
            queries.extend(
                [
                    f'"{name}" FCA enforcement',
                    f'"{name}" ICO investigation GDPR',
                ]
            )
        else:
            # Generic international regulators
            queries.append(f'"{name}" SEC FCA ASIC enforcement')

        # Industry-specific regulators
        industry = (company.industry or "").lower()
        if "fintech" in industry or "banking" in industry or "financial" in industry:
            queries.append(f'"{name}" banking regulator compliance')
        elif "health" in industry:
            queries.append(f'"{name}" HIPAA FDA compliance')
        elif "tech" in industry:
            queries.append(f'"{name}" data privacy GDPR CCPA')

        # Add ICP-specific regulatory queries
        if icp:
            keyword_str = " ".join(icp.keywords[:3])  # Use up to 3 keywords
            queries.append(f'"{name}" {keyword_str} regulatory compliance')
            if icp.description:
                queries.append(f'"{name}" {icp.description} regulation')

        return queries
