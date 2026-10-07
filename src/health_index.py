"""Predictive-maintenance health index for transformer DGA observations.

This module is an extension to the upstream transformer-health-dga project.
It does not replace the IEC/ML diagnosis. Instead, it converts diagnosis,
model confidence and longitudinal gas behaviour into a transparent asset
health score that can be used to prioritise engineering review.

The score is a decision-support indicator, not a substitute for IEC/IEEE
assessment or engineering judgement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Mapping, Optional

GASES = ("H2", "CH4", "C2H6", "C2H4", "C2H2")

# Relative diagnostic severity. Values are intentionally explicit so the
# engineering assumptions can be reviewed rather than hidden in an ML model.
FAULT_SEVERITY = {
    "Normal": 0.00,
    "PD": 0.35,
    "D1": 0.55,
    "D2": 1.00,
    "T1": 0.35,
    "T2": 0.65,
    "T3": 1.00,
}

# Gas importance for deterioration trending. Acetylene receives the largest
# weight because a rising C2H2 trend is particularly important for discharge.
TREND_WEIGHTS = {
    "H2": 0.15,
    "CH4": 0.15,
    "C2H6": 0.10,
    "C2H4": 0.25,
    "C2H2": 0.35,
}


@dataclass(frozen=True)
class HealthAssessment:
    health_index: float
    risk_score: float
    risk_category: str
    maintenance_priority: str
    fault_severity: float
    trend_severity: float
    uncertainty_penalty: float
    explanation: tuple[str, ...]

    def to_dict(self) -> dict:
        result = asdict(self)
        result["explanation"] = list(self.explanation)
        return result


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def calculate_gas_trends(
    current: Mapping[str, float],
    previous: Mapping[str, float],
    months_between: float,
) -> dict[str, float]:
    """Return gas rate-of-change in ppm/month."""
    if months_between <= 0:
        raise ValueError("months_between must be greater than zero")

    trends = {}
    for gas in GASES:
        if gas not in current or gas not in previous:
            raise KeyError(f"Missing DGA gas: {gas}")
        trends[gas] = (float(current[gas]) - float(previous[gas])) / months_between
    return trends


def _trend_severity(
    current: Mapping[str, float],
    trends_ppm_per_month: Optional[Mapping[str, float]],
) -> float:
    """Calculate a dimensionless 0-1 deterioration indicator.

    Positive monthly change is normalised against the current concentration.
    This deliberately measures acceleration/trend rather than absolute gas
    thresholds, which remain the responsibility of the existing diagnostic
    layer.
    """
    if not trends_ppm_per_month:
        return 0.0

    score = 0.0
    for gas, weight in TREND_WEIGHTS.items():
        current_value = max(float(current.get(gas, 0.0)), 1.0)
        positive_rate = max(float(trends_ppm_per_month.get(gas, 0.0)), 0.0)
        # A monthly rise equal to 25% of the present concentration saturates
        # this gas's trend contribution.
        relative_rate = _clamp(positive_rate / (0.25 * current_value))
        score += weight * relative_rate
    return _clamp(score)


def _risk_band(risk_score: float) -> tuple[str, str]:
    if risk_score >= 75:
        return "CRITICAL", "Immediate engineering investigation"
    if risk_score >= 50:
        return "HIGH", "Urgent review and increased monitoring"
    if risk_score >= 25:
        return "MODERATE", "Schedule engineering review and trend monitoring"
    return "LOW", "Continue routine condition monitoring"


def assess_transformer_health(
    gases: Mapping[str, float],
    diagnosis: str,
    confidence: float,
    trends_ppm_per_month: Optional[Mapping[str, float]] = None,
) -> HealthAssessment:
    """Create a transparent 0-100 transformer health assessment.

    Risk composition:
      65% diagnosed fault severity
      25% positive DGA deterioration trend
      10% model uncertainty

    Health index is 100 - risk score. Lower health therefore means higher
    maintenance concern.
    """
    if diagnosis not in FAULT_SEVERITY:
        raise ValueError(
            f"Unknown diagnosis '{diagnosis}'. Expected one of "
            f"{', '.join(FAULT_SEVERITY)}"
        )

    for gas in GASES:
        if gas not in gases:
            raise KeyError(f"Missing DGA gas: {gas}")
        if float(gases[gas]) < 0:
            raise ValueError(f"{gas} cannot be negative")

    confidence = _clamp(confidence)
    fault_severity = FAULT_SEVERITY[diagnosis]
    trend_severity = _trend_severity(gases, trends_ppm_per_month)
    uncertainty_penalty = 1.0 - confidence

    risk = 100.0 * (
        0.65 * fault_severity
        + 0.25 * trend_severity
        + 0.10 * uncertainty_penalty
    )
    risk = round(max(0.0, min(100.0, risk)), 1)
    health = round(100.0 - risk, 1)
    category, priority = _risk_band(risk)

    reasons = [
        f"ML/diagnostic fault class: {diagnosis}",
        f"Model confidence: {confidence * 100:.1f}%",
    ]
    if trends_ppm_per_month:
        rising = sorted(
            (
                (gas, float(rate))
                for gas, rate in trends_ppm_per_month.items()
                if gas in GASES and float(rate) > 0
            ),
            key=lambda item: item[1],
            reverse=True,
        )
        if rising:
            gas, rate = rising[0]
            reasons.append(f"Fastest rising gas: {gas} (+{rate:.1f} ppm/month)")
        else:
            reasons.append("No positive DGA trend detected")
    else:
        reasons.append("No longitudinal DGA trend supplied")

    return HealthAssessment(
        health_index=health,
        risk_score=risk,
        risk_category=category,
        maintenance_priority=priority,
        fault_severity=round(fault_severity, 3),
        trend_severity=round(trend_severity, 3),
        uncertainty_penalty=round(uncertainty_penalty, 3),
        explanation=tuple(reasons),
    )
