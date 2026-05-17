"""Rule-based signal computation engine."""

from datetime import datetime, timedelta
from typing import Optional

from app.config import get_settings
from app.schemas import (
    EvidenceItem,
    EvidenceWithEvent,
    EventType,
    FinancialSubtype,
    ICPInput,
    Recommendation,
    RecommendationReason,
    Signal,
    SignalDirection,
    SignalStatus,
    SignalType,
    SourceType,
)


class SignalEngine:
    """Computes signals from extracted events using rule-based logic."""

    # Default keywords when no ICP is provided
    DEFAULT_EXEC_KEYWORDS = [
        "compliance",
        "risk",
        "security",
        "cro",
        "ciso",
        "cco",
        "chief risk",
        "chief compliance",
        "chief security",
        "head of risk",
        "head of compliance",
        "head of security",
        "vp risk",
        "vp compliance",
        "vp security",
    ]

    def __init__(self, icp: Optional[ICPInput] = None) -> None:
        settings = get_settings()
        self.exec_recency_days = settings.exec_movement_recency_days
        self.regulatory_deadline_days = settings.regulatory_deadline_days
        self.job_openings_recency_days = settings.job_openings_recency_days
        self.tech_changes_recency_days = settings.tech_changes_recency_days
        self.budget_trends_recency_days = settings.budget_trends_recency_days
        self.icp = icp

        # Build relevance keywords from ICP or use defaults
        if icp:
            # Combine ICP keywords with variations
            self.relevance_keywords = []
            for kw in icp.keywords:
                kw_lower = kw.lower()
                self.relevance_keywords.extend([
                    kw_lower,
                    f"chief {kw_lower}",
                    f"head of {kw_lower}",
                    f"vp {kw_lower}",
                    f"director {kw_lower}",
                ])
        else:
            self.relevance_keywords = self.DEFAULT_EXEC_KEYWORDS

    def compute_signals(
        self, evidence_with_events: list[EvidenceWithEvent]
    ) -> list[Signal]:
        """Compute all signals from extracted events."""
        signals = [
            self._compute_exec_movement(evidence_with_events),
            self._compute_regulatory_pressure(evidence_with_events),
            self._compute_financial_trends(evidence_with_events),
            self._compute_job_openings(evidence_with_events),
            self._compute_tech_tool_changes(evidence_with_events),
            self._compute_budget_trends(evidence_with_events),
        ]
        return signals

    def compute_single_signal(
        self, evidence_with_events: list[EvidenceWithEvent], signal_type: SignalType
    ) -> Signal:
        """Compute a single signal type from extracted events."""
        if signal_type == SignalType.EXEC_MOVEMENT:
            return self._compute_exec_movement(evidence_with_events)
        elif signal_type == SignalType.REGULATORY_PRESSURE:
            return self._compute_regulatory_pressure(evidence_with_events)
        elif signal_type == SignalType.FINANCIAL_TRENDS:
            return self._compute_financial_trends(evidence_with_events)
        elif signal_type == SignalType.JOB_OPENINGS:
            return self._compute_job_openings(evidence_with_events)
        elif signal_type == SignalType.TECH_TOOL_CHANGES:
            return self._compute_tech_tool_changes(evidence_with_events)
        elif signal_type == SignalType.BUDGET_TRENDS:
            return self._compute_budget_trends(evidence_with_events)
        else:
            raise ValueError(f"Unknown signal type: {signal_type}")

    def _compute_exec_movement(
        self, evidence_with_events: list[EvidenceWithEvent]
    ) -> Signal:
        """Compute EXEC_MOVEMENT signal from executive hire/departure events."""
        relevant_events: list[EvidenceWithEvent] = []
        hire_count = 0
        departure_count = 0

        # Build focus area description for summaries
        if self.icp:
            focus_area = ", ".join(self.icp.keywords[:3])
        else:
            focus_area = "compliance/risk/security"

        for item in evidence_with_events:
            if item.event is None:
                continue

            if item.event.event_type in (EventType.EXEC_HIRE, EventType.EXEC_DEPARTURE):
                role = (item.event.role or "").lower()
                event_summary = item.event.summary.lower()

                # Check relevance using ICP keywords or defaults
                is_relevant = any(
                    kw in role or kw in event_summary for kw in self.relevance_keywords
                )

                # Also consider seniority
                is_senior = item.event.seniority in ("C-LEVEL", "VP", "DIRECTOR")

                if is_relevant or is_senior:
                    # Check recency
                    if self._is_recent(item.event.event_date, self.exec_recency_days):
                        relevant_events.append(item)
                        if item.event.event_type == EventType.EXEC_HIRE:
                            hire_count += 1
                        else:
                            departure_count += 1

        # Determine status and direction
        if not relevant_events:
            status = SignalStatus.NEUTRAL
            direction = SignalDirection.STABLE
            summary = f"No recent executive movements detected in {focus_area}."
            confidence = 0.3
        elif hire_count > departure_count:
            status = SignalStatus.POSITIVE
            direction = SignalDirection.GROWING
            summary = f"Recent leadership activity: {hire_count} hire(s) in {focus_area} roles."
            confidence = min(0.9, 0.5 + (hire_count * 0.15))
        elif departure_count > hire_count:
            status = SignalStatus.NEGATIVE
            direction = SignalDirection.FALLING
            summary = f"Leadership changes: {departure_count} departure(s) from {focus_area}."
            confidence = min(0.85, 0.5 + (departure_count * 0.1))
        else:
            status = SignalStatus.NEUTRAL
            direction = SignalDirection.STABLE
            summary = f"Executive activity detected: {hire_count} hire(s), {departure_count} departure(s)."
            confidence = 0.5

        return Signal(
            type=SignalType.EXEC_MOVEMENT,
            status=status,
            direction=direction,
            confidence=confidence,
            summary=summary,
            evidence=[item.evidence for item in relevant_events[:5]],
        )

    def _compute_regulatory_pressure(
        self, evidence_with_events: list[EvidenceWithEvent]
    ) -> Signal:
        """Compute REGULATORY_PRESSURE signal from regulatory events."""
        relevant_events: list[EvidenceWithEvent] = []
        action_count = 0
        deadline_count = 0

        for item in evidence_with_events:
            if item.event is None:
                continue

            if item.event.event_type in (
                EventType.REGULATORY_ACTION,
                EventType.REGULATORY_DEADLINE,
            ):
                if self._is_recent(item.event.event_date, self.regulatory_deadline_days):
                    relevant_events.append(item)
                    if item.event.event_type == EventType.REGULATORY_ACTION:
                        action_count += 1
                    else:
                        deadline_count += 1

        # Determine status and direction
        if not relevant_events:
            status = SignalStatus.NEUTRAL
            direction = SignalDirection.STABLE
            summary = "No recent regulatory actions or deadlines detected."
            confidence = 0.3
        else:
            status = SignalStatus.POSITIVE  # Positive for sales opportunity
            direction = SignalDirection.GROWING

            parts = []
            if action_count > 0:
                parts.append(f"{action_count} enforcement action(s)")
            if deadline_count > 0:
                parts.append(f"{deadline_count} compliance deadline(s)")

            summary = f"Regulatory pressure detected: {', '.join(parts)}."

            # Higher confidence with more events and amounts
            base_confidence = 0.6
            confidence = min(0.95, base_confidence + (len(relevant_events) * 0.1))

            # Boost confidence if specific amounts/regulators mentioned
            for item in relevant_events:
                if item.event and item.event.amount:
                    confidence = min(0.95, confidence + 0.1)
                    break

        return Signal(
            type=SignalType.REGULATORY_PRESSURE,
            status=status,
            direction=direction,
            confidence=confidence,
            summary=summary,
            evidence=[item.evidence for item in relevant_events[:5]],
        )

    def _compute_financial_trends(
        self, evidence_with_events: list[EvidenceWithEvent]
    ) -> Signal:
        """Compute FINANCIAL_TRENDS signal from financial events."""
        relevant_events: list[EvidenceWithEvent] = []
        positive_signals = 0
        negative_signals = 0

        positive_subtypes = {
            FinancialSubtype.FUNDING,
            FinancialSubtype.EXPANSION,
            FinancialSubtype.HIRING,
            FinancialSubtype.ACQUISITION,
        }
        negative_subtypes = {
            FinancialSubtype.LAYOFF,
            FinancialSubtype.BUDGET_CUT,
        }

        for item in evidence_with_events:
            if item.event is None:
                continue

            if item.event.event_type == EventType.FINANCIAL_EVENT:
                relevant_events.append(item)

                subtype = item.event.financial_subtype
                if subtype in positive_subtypes:
                    positive_signals += 1
                elif subtype in negative_subtypes:
                    negative_signals += 1
                elif subtype == FinancialSubtype.REVENUE_CHANGE:
                    # Check summary for direction
                    summary_lower = item.event.summary.lower()
                    if any(
                        kw in summary_lower
                        for kw in ["growth", "increase", "up", "grew", "profit"]
                    ):
                        positive_signals += 1
                    elif any(
                        kw in summary_lower
                        for kw in ["decline", "decrease", "down", "loss", "fell"]
                    ):
                        negative_signals += 1

        # Determine status and direction
        if not relevant_events:
            status = SignalStatus.NEUTRAL
            direction = SignalDirection.STABLE
            summary = "No significant financial events detected."
            confidence = 0.3
        elif positive_signals > negative_signals:
            status = SignalStatus.POSITIVE
            direction = SignalDirection.GROWING
            summary = f"Positive financial signals: {positive_signals} growth indicator(s) detected."
            confidence = min(0.9, 0.5 + (positive_signals * 0.12))
        elif negative_signals > positive_signals:
            status = SignalStatus.NEGATIVE
            direction = SignalDirection.FALLING
            summary = f"Financial caution: {negative_signals} negative indicator(s) detected."
            confidence = min(0.85, 0.5 + (negative_signals * 0.1))
        else:
            status = SignalStatus.NEUTRAL
            direction = SignalDirection.STABLE
            summary = f"Mixed financial signals: {positive_signals} positive, {negative_signals} negative."
            confidence = 0.5

        return Signal(
            type=SignalType.FINANCIAL_TRENDS,
            status=status,
            direction=direction,
            confidence=confidence,
            summary=summary,
            evidence=[item.evidence for item in relevant_events[:5]],
        )

    def _compute_job_openings(
        self, evidence_with_events: list[EvidenceWithEvent]
    ) -> Signal:
        """Compute JOB_OPENINGS signal from job posting events."""
        relevant_events: list[EvidenceWithEvent] = []
        posting_count = 0

        for item in evidence_with_events:
            if item.event is None:
                continue

            if item.event.event_type == EventType.JOB_POSTING:
                if self._is_recent(item.event.event_date, self.job_openings_recency_days):
                    relevant_events.append(item)
                    posting_count += 1

        # Determine status and direction
        # Active hiring = positive signal for sales (company has budget)
        if not relevant_events:
            status = SignalStatus.NEUTRAL
            direction = SignalDirection.STABLE
            summary = "No recent job openings detected."
            confidence = 0.3
        else:
            status = SignalStatus.POSITIVE
            direction = SignalDirection.GROWING
            summary = f"Active hiring detected: {posting_count} job opening(s) found."
            confidence = min(0.9, 0.5 + (posting_count * 0.1))

        return Signal(
            type=SignalType.JOB_OPENINGS,
            status=status,
            direction=direction,
            confidence=confidence,
            summary=summary,
            evidence=[item.evidence for item in relevant_events[:5]],
        )

    def _compute_tech_tool_changes(
        self, evidence_with_events: list[EvidenceWithEvent]
    ) -> Signal:
        """Compute TECH_TOOL_CHANGES signal from technology adoption/migration events."""
        relevant_events: list[EvidenceWithEvent] = []
        adoption_count = 0
        migration_count = 0

        for item in evidence_with_events:
            if item.event is None:
                continue

            if item.event.event_type in (EventType.TECH_ADOPTION, EventType.TECH_MIGRATION):
                if self._is_recent(item.event.event_date, self.tech_changes_recency_days):
                    relevant_events.append(item)
                    if item.event.event_type == EventType.TECH_ADOPTION:
                        adoption_count += 1
                    else:
                        migration_count += 1

        # Determine status and direction
        # Tech investment = positive signal for sales
        if not relevant_events:
            status = SignalStatus.NEUTRAL
            direction = SignalDirection.STABLE
            summary = "No recent technology changes detected."
            confidence = 0.3
        else:
            status = SignalStatus.POSITIVE
            direction = SignalDirection.GROWING
            parts = []
            if adoption_count > 0:
                parts.append(f"{adoption_count} adoption(s)")
            if migration_count > 0:
                parts.append(f"{migration_count} migration(s)")
            summary = f"Technology investment detected: {', '.join(parts)}."
            confidence = min(0.9, 0.5 + (len(relevant_events) * 0.12))

        return Signal(
            type=SignalType.TECH_TOOL_CHANGES,
            status=status,
            direction=direction,
            confidence=confidence,
            summary=summary,
            evidence=[item.evidence for item in relevant_events[:5]],
        )

    def _compute_budget_trends(
        self, evidence_with_events: list[EvidenceWithEvent]
    ) -> Signal:
        """Compute BUDGET_TRENDS signal from budget change events."""
        relevant_events: list[EvidenceWithEvent] = []
        increase_count = 0
        decrease_count = 0

        for item in evidence_with_events:
            if item.event is None:
                continue

            if item.event.event_type == EventType.BUDGET_CHANGE:
                if self._is_recent(item.event.event_date, self.budget_trends_recency_days):
                    relevant_events.append(item)
                    # Check summary for direction
                    summary_lower = item.event.summary.lower()
                    if any(
                        kw in summary_lower
                        for kw in ["increase", "growth", "expand", "boost", "raise", "invest"]
                    ):
                        increase_count += 1
                    elif any(
                        kw in summary_lower
                        for kw in ["cut", "reduce", "decrease", "freeze", "slash", "constraint"]
                    ):
                        decrease_count += 1

        # Determine status and direction
        if not relevant_events:
            status = SignalStatus.NEUTRAL
            direction = SignalDirection.STABLE
            summary = "No recent budget changes detected."
            confidence = 0.3
        elif increase_count > decrease_count:
            status = SignalStatus.POSITIVE
            direction = SignalDirection.GROWING
            summary = f"Budget increase detected: {increase_count} positive indicator(s)."
            confidence = min(0.9, 0.5 + (increase_count * 0.12))
        elif decrease_count > increase_count:
            status = SignalStatus.NEGATIVE
            direction = SignalDirection.FALLING
            summary = f"Budget constraints detected: {decrease_count} reduction indicator(s)."
            confidence = min(0.85, 0.5 + (decrease_count * 0.1))
        else:
            status = SignalStatus.NEUTRAL
            direction = SignalDirection.STABLE
            summary = f"Mixed budget signals: {increase_count} increase(s), {decrease_count} decrease(s)."
            confidence = 0.5

        return Signal(
            type=SignalType.BUDGET_TRENDS,
            status=status,
            direction=direction,
            confidence=confidence,
            summary=summary,
            evidence=[item.evidence for item in relevant_events[:5]],
        )

    def _is_recent(self, event_date: Optional[str], days: int) -> bool:
        """Check if an event date is within the specified number of days."""
        if not event_date:
            # If no date, assume it might be recent
            return True

        try:
            date = datetime.strptime(event_date, "%Y-%m-%d")
            cutoff = datetime.now() - timedelta(days=days)
            return date >= cutoff
        except ValueError:
            return True  # Can't parse, assume recent

    def compute_recommendation(
        self, signals: list[Signal]
    ) -> tuple[Recommendation, list[RecommendationReason]]:
        """Compute overall recommendation based on signals."""
        reasons: list[RecommendationReason] = []
        positive_count = 0
        negative_count = 0

        for signal in signals:
            if signal.type == SignalType.EXEC_MOVEMENT:
                if signal.status == SignalStatus.POSITIVE:
                    reasons.append(RecommendationReason.RECENT_EXEC_HIRE)
                    positive_count += 1

            elif signal.type == SignalType.REGULATORY_PRESSURE:
                if signal.status == SignalStatus.POSITIVE and signal.confidence > 0.5:
                    # Check evidence for fines vs deadlines
                    has_fine = any(
                        "fine" in e.snippet.lower() or "penalty" in e.snippet.lower()
                        for e in signal.evidence
                    )
                    if has_fine:
                        reasons.append(RecommendationReason.REGULATORY_FINE)
                    else:
                        reasons.append(RecommendationReason.REGULATORY_DEADLINE)
                    positive_count += 1

            elif signal.type == SignalType.FINANCIAL_TRENDS:
                if signal.status == SignalStatus.POSITIVE:
                    # Check for specific positive signals
                    has_funding = any(
                        "funding" in e.snippet.lower() or "raised" in e.snippet.lower()
                        for e in signal.evidence
                    )
                    if has_funding:
                        reasons.append(RecommendationReason.RECENT_FUNDING)
                    else:
                        reasons.append(RecommendationReason.EXPANSION_SIGNALS)
                    positive_count += 1
                elif signal.status == SignalStatus.NEGATIVE:
                    reasons.append(RecommendationReason.FINANCIAL_DISTRESS)
                    negative_count += 1

            elif signal.type == SignalType.JOB_OPENINGS:
                if signal.status == SignalStatus.POSITIVE:
                    reasons.append(RecommendationReason.ACTIVE_HIRING)
                    positive_count += 1

            elif signal.type == SignalType.TECH_TOOL_CHANGES:
                if signal.status == SignalStatus.POSITIVE:
                    reasons.append(RecommendationReason.TECH_INVESTMENT)
                    positive_count += 1

            elif signal.type == SignalType.BUDGET_TRENDS:
                if signal.status == SignalStatus.POSITIVE:
                    reasons.append(RecommendationReason.BUDGET_INCREASE)
                    positive_count += 1
                elif signal.status == SignalStatus.NEGATIVE:
                    reasons.append(RecommendationReason.BUDGET_DECREASE)
                    negative_count += 1

        # Determine recommendation
        if not reasons:
            return Recommendation.MONITOR, [RecommendationReason.NO_SIGNALS]
        elif negative_count > positive_count:
            return Recommendation.AVOID, reasons
        elif positive_count >= 2 or (positive_count == 1 and negative_count == 0):
            return Recommendation.CONTACT, reasons
        else:
            return Recommendation.MONITOR, reasons
