"""Pydantic models for request/response schemas."""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


# Enums
class SignalType(str, Enum):
    EXEC_MOVEMENT = "EXEC_MOVEMENT"
    REGULATORY_PRESSURE = "REGULATORY_PRESSURE"
    FINANCIAL_TRENDS = "FINANCIAL_TRENDS"
    JOB_OPENINGS = "JOB_OPENINGS"
    TECH_TOOL_CHANGES = "TECH_TOOL_CHANGES"
    BUDGET_TRENDS = "BUDGET_TRENDS"


class SignalStatus(str, Enum):
    POSITIVE = "POSITIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"


class SignalDirection(str, Enum):
    GROWING = "GROWING"
    FALLING = "FALLING"
    STABLE = "STABLE"


class SourceType(str, Enum):
    NEWS = "news"
    REGULATORY = "regulatory"
    FINANCIAL = "financial"
    PRESS_RELEASE = "press_release"
    SEC_FILING = "sec_filing"


class EventType(str, Enum):
    EXEC_HIRE = "EXEC_HIRE"
    EXEC_DEPARTURE = "EXEC_DEPARTURE"
    REGULATORY_ACTION = "REGULATORY_ACTION"
    REGULATORY_DEADLINE = "REGULATORY_DEADLINE"
    FINANCIAL_EVENT = "FINANCIAL_EVENT"
    JOB_POSTING = "JOB_POSTING"
    TECH_ADOPTION = "TECH_ADOPTION"
    TECH_MIGRATION = "TECH_MIGRATION"
    BUDGET_CHANGE = "BUDGET_CHANGE"
    OTHER = "OTHER"


class FinancialSubtype(str, Enum):
    FUNDING = "FUNDING"
    LAYOFF = "LAYOFF"
    REVENUE_CHANGE = "REVENUE_CHANGE"
    ACQUISITION = "ACQUISITION"
    BUDGET_CUT = "BUDGET_CUT"
    EXPANSION = "EXPANSION"
    HIRING = "HIRING"


class Recommendation(str, Enum):
    CONTACT = "CONTACT"
    MONITOR = "MONITOR"
    AVOID = "AVOID"


class RecommendationReason(str, Enum):
    RECENT_EXEC_HIRE = "RECENT_EXEC_HIRE"
    REGULATORY_DEADLINE = "REGULATORY_DEADLINE"
    REGULATORY_FINE = "REGULATORY_FINE"
    RECENT_FUNDING = "RECENT_FUNDING"
    EXPANSION_SIGNALS = "EXPANSION_SIGNALS"
    FINANCIAL_DISTRESS = "FINANCIAL_DISTRESS"
    ACTIVE_HIRING = "ACTIVE_HIRING"
    TECH_INVESTMENT = "TECH_INVESTMENT"
    BUDGET_INCREASE = "BUDGET_INCREASE"
    BUDGET_DECREASE = "BUDGET_DECREASE"
    NO_SIGNALS = "NO_SIGNALS"


# Input Models
class CompanyInput(BaseModel):
    name: str = Field(..., min_length=1, description="Company name")
    domain: str = Field(..., min_length=1, description="Company domain (e.g., acme.com)")
    country: Optional[str] = Field(None, description="Country code (e.g., AU, US)")
    industry: Optional[str] = Field(None, description="Industry sector")


class PersonInput(BaseModel):
    name: Optional[str] = Field(None, description="Contact person name")
    role: Optional[str] = Field(None, description="Contact person role/title")
    email: Optional[str] = Field(None, description="Contact email")


class ICPInput(BaseModel):
    """Ideal Customer Profile for filtering relevant signals."""

    keywords: list[str] = Field(
        ..., min_length=1, description="Keywords describing target roles, departments, or focus areas"
    )
    description: Optional[str] = Field(
        None, description="Free-form description of ideal customer profile"
    )


class SignalRequest(BaseModel):
    company: CompanyInput
    person: Optional[PersonInput] = None
    signal_types: Optional[list[SignalType]] = Field(
        None, description="Filter to specific signal types (default: all)"
    )
    icp: Optional[ICPInput] = Field(
        None, description="Ideal Customer Profile to filter relevant signals"
    )


class SingleSignalRequest(BaseModel):
    """Request body for single signal type endpoint."""

    company: CompanyInput
    person: Optional[PersonInput] = None
    icp: Optional[ICPInput] = Field(
        None, description="Ideal Customer Profile to filter relevant signals"
    )


# Evidence Models
class EvidenceItem(BaseModel):
    source_type: SourceType
    title: str
    url: str
    published_at: Optional[str] = Field(None, description="Publication date (YYYY-MM-DD)")
    snippet: str = Field(..., description="Relevant text excerpt")
    raw_content: Optional[str] = Field(None, description="Full content for extraction")


# Extracted Event Models
class ExtractedEvent(BaseModel):
    event_type: EventType
    financial_subtype: Optional[FinancialSubtype] = None
    entity_name: Optional[str] = Field(None, description="Person or org involved")
    role: Optional[str] = Field(None, description="Role/title if exec movement")
    seniority: Optional[str] = Field(None, description="Seniority level: C-LEVEL, VP, DIRECTOR, MANAGER")
    event_date: Optional[str] = Field(None, description="When the event occurred (YYYY-MM-DD)")
    amount: Optional[str] = Field(None, description="Amount if applicable (e.g., $10M)")
    regulator: Optional[str] = Field(None, description="Regulatory body if applicable")
    summary: str = Field(..., description="Brief summary of the event")
    relevance_score: float = Field(0.5, ge=0.0, le=1.0, description="How relevant to signal detection")


# Signal Models
class Signal(BaseModel):
    type: SignalType
    status: SignalStatus
    direction: SignalDirection
    confidence: float = Field(..., ge=0.0, le=1.0)
    summary: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class SignalResponse(BaseModel):
    company_domain: str
    analyzed_at: datetime
    signals: list[Signal]
    recommendation: Recommendation
    recommendation_reasons: list[RecommendationReason]


class SingleSignalResponse(BaseModel):
    """Response for single signal type endpoint."""

    company_domain: str
    analyzed_at: datetime
    signal: Signal


# Internal Models for Processing
class EvidenceWithEvent(BaseModel):
    evidence: EvidenceItem
    event: Optional[ExtractedEvent] = None
