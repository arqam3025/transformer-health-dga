"""Fleet-level transformer maintenance prioritisation.

Ranks multiple transformer predictive-maintenance assessments so engineering
teams can focus first on assets with the highest condition risk. The ranking
uses the transparent risk score produced by predictive_maintenance.py, with
small escalation factors for rapid deterioration and critical DGA fault classes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

from src.predictive_maintenance import (
    PredictiveMaintenanceAssessment,
    assess_history,
)


@dataclass(frozen=True)
class FleetAsset:
    rank: int
    transformer_id: str
    priority_score: float
    risk_category: str
    health_index: float
    diagnosis: str
    trend_status: str
    dominant_rising_gas: str | None
    dominant_rate_ppm_per_month: float
    maintenance_priority: str
    recommendation: str

    def to_dict(self) -> dict:
        return asdict(self)


def _priority_score(assessment: PredictiveMaintenanceAssessment) -> float:
    """Return transparent 0-100 fleet priority score."""
    score = float(assessment.risk_score)

    if assessment.trend_status == "RAPID DETERIORATION":
        score += 8.0
    elif assessment.trend_status == "DETERIORATING":
        score += 4.0

    if assessment.diagnosis in {"D2", "T3"}:
        score += 7.0
    elif assessment.diagnosis in {"D1", "T2"}:
        score += 3.0

    return round(min(100.0, score), 1)


def rank_assessments(
    assessments: Iterable[PredictiveMaintenanceAssessment],
) -> list[FleetAsset]:
    """Rank already-assessed transformers from most to least urgent."""
    rows = list(assessments)
    rows.sort(
        key=lambda item: (
            _priority_score(item),
            item.risk_score,
            -item.health_index,
        ),
        reverse=True,
    )

    return [
        FleetAsset(
            rank=index,
            transformer_id=item.transformer_id,
            priority_score=_priority_score(item),
            risk_category=item.risk_category,
            health_index=item.health_index,
            diagnosis=item.diagnosis,
            trend_status=item.trend_status,
            dominant_rising_gas=item.dominant_rising_gas,
            dominant_rate_ppm_per_month=item.dominant_rate_ppm_per_month,
            maintenance_priority=item.maintenance_priority,
            recommendation=item.recommendation,
        )
        for index, item in enumerate(rows, start=1)
    ]


def assess_fleet(assets: Iterable[Mapping]) -> list[FleetAsset]:
    """Assess and rank a fleet.

    Each asset requires:
      transformer_id
      observations
      diagnostic_result

    This boundary lets callers obtain diagnostic_result from the existing
    calibrated model while keeping fleet ranking independently testable.
    """
    assessments = []
    for asset in assets:
        for required in ("transformer_id", "observations", "diagnostic_result"):
            if required not in asset:
                raise KeyError(f"Fleet asset requires '{required}'")

        assessments.append(
            assess_history(
                transformer_id=str(asset["transformer_id"]),
                observations=asset["observations"],
                diagnostic_result=asset["diagnostic_result"],
            )
        )

    return rank_assessments(assessments)


def fleet_summary(ranked_assets: Iterable[FleetAsset]) -> dict:
    """Return compact management-level fleet condition counts."""
    rows = list(ranked_assets)
    categories = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0}
    for asset in rows:
        categories[asset.risk_category] = (
            categories.get(asset.risk_category, 0) + 1
        )

    return {
        "total_transformers": len(rows),
        "critical": categories["CRITICAL"],
        "high": categories["HIGH"],
        "moderate": categories["MODERATE"],
        "low": categories["LOW"],
        "highest_priority_transformer": (
            rows[0].transformer_id if rows else None
        ),
    }
