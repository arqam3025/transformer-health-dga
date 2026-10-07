"""Streamlit dashboard for transformer predictive-maintenance intelligence.

Run:
    streamlit run dashboard.py

The sample fleet below is synthetic demonstration data. Replace it with
timestamped transformer DGA histories and diagnostic outputs from the existing
model/integration layer for operational use.
"""

import pandas as pd
import streamlit as st

from src.fleet_prioritization import assess_fleet, fleet_summary


st.set_page_config(
    page_title="Transformer Asset Health Intelligence",
    page_icon="⚡",
    layout="wide",
)


def obs(timestamp, h2, ch4, c2h6, c2h4, c2h2):
    return {
        "timestamp": timestamp,
        "gases": {
            "H2": h2,
            "CH4": ch4,
            "C2H6": c2h6,
            "C2H4": c2h4,
            "C2H2": c2h2,
        },
    }


# Synthetic examples for portfolio demonstration only.
DEMO_FLEET = [
    {
        "transformer_id": "TR-001",
        "observations": [
            obs("2026-01-01", 20, 8, 4, 2, 0),
            obs("2026-02-01", 21, 8, 4, 2, 0),
            obs("2026-03-01", 21, 9, 4, 2, 0),
        ],
        "diagnostic_result": {"diagnosis": "Normal", "confidence": 0.96},
    },
    {
        "transformer_id": "TR-009",
        "observations": [
            obs("2026-01-01", 65, 330, 105, 160, 3),
            obs("2026-02-01", 72, 410, 102, 225, 4),
            obs("2026-03-01", 82, 510, 100, 310, 5),
        ],
        "diagnostic_result": {"diagnosis": "T2", "confidence": 0.89},
    },
    {
        "transformer_id": "TR-017",
        "observations": [
            obs("2026-01-01", 250, 30, 10, 80, 80),
            obs("2026-02-01", 350, 40, 10, 130, 180),
            obs("2026-03-01", 500, 50, 10, 200, 400),
        ],
        "diagnostic_result": {"diagnosis": "D2", "confidence": 0.93},
    },
    {
        "transformer_id": "TR-024",
        "observations": [
            obs("2026-01-01", 55, 220, 120, 38, 1),
            obs("2026-02-01", 58, 250, 130, 42, 1),
            obs("2026-03-01", 62, 290, 145, 48, 2),
        ],
        "diagnostic_result": {"diagnosis": "T1", "confidence": 0.86},
    },
]


ranked = assess_fleet(DEMO_FLEET)
summary = fleet_summary(ranked)

st.title("⚡ Transformer Asset Health Intelligence")
st.caption(
    "AI-enabled DGA condition monitoring, deterioration analysis and "
    "maintenance prioritisation — portfolio demonstration with synthetic data."
)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Fleet size", summary["total_transformers"])
c2.metric("Critical", summary["critical"])
c3.metric("High risk", summary["high"])
c4.metric("Moderate", summary["moderate"])
c5.metric("Low risk", summary["low"])

st.subheader("Maintenance priority queue")
table = pd.DataFrame([item.to_dict() for item in ranked])
display_columns = [
    "rank",
    "transformer_id",
    "priority_score",
    "risk_category",
    "health_index",
    "diagnosis",
    "trend_status",
    "maintenance_priority",
]
st.dataframe(
    table[display_columns],
    use_container_width=True,
    hide_index=True,
)

st.subheader("Asset investigation")
selected_id = st.selectbox(
    "Select transformer",
    [item.transformer_id for item in ranked],
)
selected = next(
    item for item in ranked if item.transformer_id == selected_id
)
source = next(
    asset for asset in DEMO_FLEET
    if asset["transformer_id"] == selected_id
)

a, b, c, d = st.columns(4)
a.metric("Health Index", f"{selected.health_index:.1f}/100")
b.metric("Risk", selected.risk_category)
c.metric("Fault diagnosis", selected.diagnosis)
d.metric("Priority score", f"{selected.priority_score:.1f}/100")

st.write("**Maintenance recommendation**")
st.info(selected.recommendation)

history_rows = []
for row in source["observations"]:
    history_rows.append(
        {"timestamp": row["timestamp"], **row["gases"]}
    )
history_df = pd.DataFrame(history_rows)
history_df["timestamp"] = pd.to_datetime(history_df["timestamp"])
history_df = history_df.set_index("timestamp")

st.write("**DGA gas history (ppm)**")
st.line_chart(history_df)

left, right = st.columns(2)
with left:
    st.write("**Condition evidence**")
    st.write(f"- Trend status: {selected.trend_status}")
    st.write(
        f"- Dominant rising gas: "
        f"{selected.dominant_rising_gas or 'None'}"
    )
    st.write(
        f"- Dominant rate: "
        f"{selected.dominant_rate_ppm_per_month:.2f} ppm/month"
    )
    confidence = source["diagnostic_result"]["confidence"] * 100
    st.write(f"- Diagnostic confidence: {confidence:.1f}%")

with right:
    st.write("**Engineering use**")
    st.write(
        "Use this view to prioritise condition review, compare assets, "
        "and inspect developing DGA patterns. Final maintenance decisions "
        "must remain subject to appropriate standards, test evidence and "
        "qualified engineering judgement."
    )

st.divider()
st.caption(
    "Demo data are synthetic and are not evidence of real transformer "
    "performance or field validation."
)
