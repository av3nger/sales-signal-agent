"""Evidence adapters for collecting sales signals."""

from .base import BaseAdapter
from .news import NewsAdapter
from .regulatory import RegulatoryAdapter
from .financial import FinancialAdapter
from .jobs import JobsAdapter
from .tech import TechAdapter
from .budget import BudgetAdapter

__all__ = [
    "BaseAdapter",
    "NewsAdapter",
    "RegulatoryAdapter",
    "FinancialAdapter",
    "JobsAdapter",
    "TechAdapter",
    "BudgetAdapter",
]
