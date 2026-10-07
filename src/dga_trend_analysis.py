"""Longitudinal DGA deterioration analysis for transformer condition monitoring.

This extension analyses repeated dissolved-gas measurements for one transformer.
It estimates gas rates of change and acceleration, identifies the dominant
deteriorating gas, and produces a trend status that can feed the transparent
health-index engine.

This is decision-support logic and does not replace IEC/IEEE interpretation or
engineering judgement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Iterable, Mapping

from src.health_index import GASES, calculate_gas_trends


@dataclass(frozen=True)
class TrendAssessment:
    observations: int
    period_months: float
    trends_ppm_per_month: dict[str, float]
    acceleration_ppm_per_month2: dict[str, float]
    dominant_rising_gas: str | None
    dominant_rate: float
    status: str
    explanation: tuple[str, ...]

    def to_dict(self) -> dict:
        result = asdict(self)
        result["explanation"] = list(self.explanation)
        return result


def _parse_timestamp(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace("Z", "+00:00"))


def _months_between(start: datetime, end: datetime) -> float:
    seconds = (end - start).total_seconds()
    if seconds <= 0:
        raise ValueError("DGA observations must have increasing timestamps")
    return seconds / (30.4375 * 24 * 3600)


def _validate_observation(observation: Mapping) -> None:
    if "timestamp" not in observation:
        raise KeyError("Each DGA observation requires a timestamp")
    gases = observation.get("gases", observation)
    for gas in GASES:
        if gas not in gases:
            raise KeyError(f"Missing DGA gas: {gas}")
        if float(gases[gas]) < 0:
            raise ValueError(f"{gas} cannot be negative")


def _gas_values(observation: Mapping) -> dict[str, float]:
    source = observation.get("gases", observation)
    return {gas: float(source[gas]) for gas in GASES}


def analyse_dga_history(observations: Iterable[Mapping]) -> TrendAssessment:
    """Analyse at least two timestamped DGA observations.

    Overall trend is measured from first to latest sample. With three or more
    samples, acceleration compares the recent gas-rate with the preceding
    interval. Status thresholds are deliberately transparent heuristics based
    on relative monthly growth, not IEC alarm limits.
    """
    rows = list(observations)
    if len(rows) < 2:
        raise ValueError("At least two DGA observations are required")

    for row in rows:
        _validate_observation(row)

    rows.sort(key=lambda row: _parse_timestamp(row["timestamp"]))
    times = [_parse_timestamp(row["timestamp"]) for row in rows]

    if len(set(times)) != len(times):
        raise ValueError("DGA observations must have unique timestamps")

    first_gases = _gas_values(rows[0])
    latest_gases = _gas_values(rows[-1])
    period_months = _months_between(times[0], times[-1])
    trends = calculate_gas_trends(latest_gases, first_gases, period_months)

    acceleration = {gas: 0.0 for gas in GASES}
    if len(rows) >= 3:
        prev_gases = _gas_values(rows[-2])
        earlier_gases = _gas_values(rows[-3])
        recent_months = _months_between(times[-2], times[-1])
        previous_months = _months_between(times[-3], times[-2])
        recent_rate = calculate_gas_trends(
            latest_gases, prev_gases, recent_months
        )
        previous_rate = calculate_gas_trends(
            prev_gases, earlier_gases, previous_months
        )
        for gas in GASES:
            mean_interval = (recent_months + previous_months) / 2.0
            acceleration[gas] = (
                recent_rate[gas] - previous_rate[gas]
            ) / mean_interval

    positive = [(gas, rate) for gas, rate in trends.items() if rate > 0]
    dominant_gas, dominant_rate = (
        max(positive, key=lambda item: item[1])
        if positive else (None, 0.0)
    )

    # Relative monthly growth allows gases with different ppm scales to be
    # compared. Current value is used only as a normaliser.
    relative_growth = {}
    for gas in GASES:
        current = max(latest_gases[gas], 1.0)
        relative_growth[gas] = max(trends[gas], 0.0) / current

    max_growth = max(relative_growth.values())
    accelerating_gases = [
        gas for gas, value in acceleration.items() if value > 0
    ]

    if max_growth >= 0.20:
        status = "RAPID DETERIORATION"
    elif max_growth >= 0.05:
        status = "DETERIORATING"
    elif max_growth > 0:
        status = "SLOW CHANGE"
    else:
        status = "STABLE/DECLINING"

    reasons = [
        f"Analysed {len(rows)} observations across {period_months:.2f} months",
        f"Trend status: {status}",
    ]
    if dominant_gas:
        reasons.append(
            f"Dominant rising gas: {dominant_gas} "
            f"(+{dominant_rate:.2f} ppm/month)"
        )
    else:
        reasons.append("No gas has a positive overall trend")

    if accelerating_gases:
        reasons.append(
            "Positive acceleration detected in: "
            + ", ".join(accelerating_gases)
        )

    return TrendAssessment(
        observations=len(rows),
        period_months=round(period_months, 3),
        trends_ppm_per_month={
            gas: round(rate, 3) for gas, rate in trends.items()
        },
        acceleration_ppm_per_month2={
            gas: round(value, 3) for gas, value in acceleration.items()
        },
        dominant_rising_gas=dominant_gas,
        dominant_rate=round(dominant_rate, 3),
        status=status,
        explanation=tuple(reasons),
    )


def latest_gases(observations: Iterable[Mapping]) -> dict[str, float]:
    """Return DGA values from the chronologically latest observation."""
    rows = list(observations)
    if not rows:
        raise ValueError("At least one DGA observation is required")
    for row in rows:
        _validate_observation(row)
    latest = max(rows, key=lambda row: _parse_timestamp(row["timestamp"]))
    return _gas_values(latest)
