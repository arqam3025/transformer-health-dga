"""Integrated predictive-maintenance engine for transformer DGA histories.

Combines the upstream diagnostic model output with the extension's longitudinal
DGA trend analysis and transparent health-index logic. The diagnostic function
is injectable so this module can be tested independently of model artefacts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Iterable, Mapping

from src.dga_trend_analysis import analyse_dga_history, latest_gases
from src.health_index import HealthAssessment, assess_transformer_health


@dataclass(frozen=True)
class PredictiveMaintenanceAssessment:
    transformer_id: str
    diagnosis: str
    confidence: float
    health_index: float
    risk_score: float
    risk_category: str
    maintenance_priority: str
    trend_status: str
    dominant_rising_gas: str | None
    dominant_rate_ppm_per_month: float
    recommendation: str
    evidence: tuple[str, ...]

    def to_dict(self) -> dict:
        result = asdict(self)
        result["evidence"] = list(self.evidence)
        return result


def _recommendation(
    health: HealthAssessment,
    trend_status: str,
    diagnosis: str,
) -> str:
    if health.risk_category == "CRITICAL":
        return (
            "Immediate engineering investigation; review DGA history and "
            "existing IEC diagnostic guidance before continued operation."
        )
    if health.risk_category == "HIGH" or trend_status == "RAPID DETERIORATION":
        return (
            "Urgent engineering review; shorten the sampling interval and "
            "investigate the developing fault."
        )
    if health.risk_category == "MODERATE" or trend_status == "DETERIORATING":
        return (
            "Schedule condition review and continue enhanced DGA trend "
            "monitoring."
        )
    if diagnosis != "Normal":
        return (
            "Continue increased monitoring and review the diagnosed condition "
            "using the existing IEC guidance."
        )
    return "Continue routine condition monitoring."


def assess_history(
    transformer_id: str,
    observations: Iterable[Mapping],
    diagnostic_result: Mapping,
) -> PredictiveMaintenanceAssessment:
    """Combine an existing diagnosis with longitudinal condition evidence.

    diagnostic_result must contain:
      diagnosis: upstream model fault class
      confidence: probability/confidence in [0, 1]
    """
    rows = list(observations)
    trend = analyse_dga_history(rows)
    gases = latest_gases(rows)

    if "diagnosis" not in diagnostic_result:
        raise KeyError("diagnostic_result requires 'diagnosis'")
    if "confidence" not in diagnostic_result:
        raise KeyError("diagnostic_result requires 'confidence'")

    diagnosis = str(diagnostic_result["diagnosis"])
    confidence = float(diagnostic_result["confidence"])

    health = assess_transformer_health(
        gases=gases,
        diagnosis=diagnosis,
        confidence=confidence,
        trends_ppm_per_month=trend.trends_ppm_per_month,
    )

    evidence = [
        f"Diagnosis: {diagnosis}",
        f"Diagnostic confidence: {confidence * 100:.1f}%",
        f"Trend status: {trend.status}",
        f"Health index: {health.health_index:.1f}/100",
        f"Risk category: {health.risk_category}",
    ]
    if trend.dominant_rising_gas:
        evidence.append(
            f"Dominant rising gas: {trend.dominant_rising_gas} "
            f"(+{trend.dominant_rate:.2f} ppm/month)"
        )

    return PredictiveMaintenanceAssessment(
        transformer_id=str(transformer_id),
        diagnosis=diagnosis,
        confidence=round(confidence, 4),
        health_index=health.health_index,
        risk_score=health.risk_score,
        risk_category=health.risk_category,
        maintenance_priority=health.maintenance_priority,
        trend_status=trend.status,
        dominant_rising_gas=trend.dominant_rising_gas,
        dominant_rate_ppm_per_month=trend.dominant_rate,
        recommendation=_recommendation(health, trend.status, diagnosis),
        evidence=tuple(evidence),
    )


def assess_with_model(
    transformer_id: str,
    observations: Iterable[Mapping],
    diagnose: Callable[[Mapping[str, float]], Mapping],
) -> PredictiveMaintenanceAssessment:
    """Run a supplied diagnostic function on the latest sample then assess it.

    The callable boundary lets the existing calibrated XGBoost model, a future
    API, or a test double be plugged into the maintenance engine without
    coupling the asset-health logic to one model implementation.
    """
    rows = list(observations)
    gases = latest_gases(rows)
    diagnostic_result = diagnose(gases)
    return assess_history(transformer_id, rows, diagnostic_result)
