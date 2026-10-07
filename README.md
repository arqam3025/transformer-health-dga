# Transformer Asset Health Intelligence — DGA, ML & Predictive Maintenance

[![Predictive Maintenance CI](https://github.com/arqam3025/transformer-health-dga/actions/workflows/predictive-maintenance-ci.yml/badge.svg?branch=feature%2Fpredictive-maintenance-extension)](https://github.com/arqam3025/transformer-health-dga/actions/workflows/predictive-maintenance-ci.yml)

An engineering portfolio extension for **AI-assisted transformer condition monitoring and predictive maintenance**. The project combines an existing dissolved-gas-analysis (DGA) fault-diagnosis pipeline with longitudinal gas-trend analysis, transparent asset health/risk scoring, fleet maintenance prioritisation and a Streamlit engineering dashboard.

> **Attribution:** This repository is a fork of [AR0714/transformer-health-dga](https://github.com/AR0714/transformer-health-dga), created by **Ankit Raj** and released under the MIT License. The upstream project provides the DGA fault-classification, classical diagnostic, explainability, RAG/LLM and original dashboard foundations. The predictive-maintenance extension described below was subsequently developed in this fork by **Raja Arqam Abdullah**. The original copyright and MIT license are retained.

## Why this extension exists

The upstream project diagnoses transformer condition from a DGA snapshot. In practical asset management, engineers also need to know whether gas concentrations are **changing over time**, how condition evidence affects an asset-level risk score, and which transformer should be investigated first across a fleet.

This extension adds that longitudinal decision-support layer:

```text
Timestamped DGA history
        |
        v
DGA trend + acceleration analysis
        |
        +--------------------+
        |                    |
        v                    v
Latest gas state       Fault diagnosis
        |              (upstream model/
        |               diagnostic result)
        +---------+----------+
                  |
                  v
        Transformer health index
        + transparent risk score
                  |
                  v
        Maintenance recommendation
                  |
                  v
          Fleet prioritisation
                  |
                  v
     Streamlit engineering dashboard
```

## Predictive-maintenance extension

| Component | Purpose |
|---|---|
| `src/dga_trend_analysis.py` | Calculates gas rates in ppm/month, trend status, acceleration and dominant rising gas from timestamped DGA observations. |
| `src/health_index.py` | Produces a transparent 0–100 health index and risk category from diagnosis severity, gas trends and diagnostic uncertainty. |
| `src/predictive_maintenance.py` | Integrates diagnosis, trend evidence and health assessment into one maintenance assessment and recommendation. |
| `src/fleet_prioritization.py` | Ranks multiple transformers so engineering teams can focus on the most urgent assets first. |
| `dashboard.py` | Streamlit portfolio dashboard for fleet KPIs, priority queue, asset investigation and DGA history. |
| `tests/` | Unit and integration tests for the extension. |
| `.github/workflows/predictive-maintenance-ci.yml` | Runs the extension test suite on Python 3.10, 3.11 and 3.12. |

### Dashboard outputs

The demonstration dashboard provides:

- fleet counts by CRITICAL / HIGH / MODERATE / LOW risk;
- a ranked maintenance-priority queue;
- per-transformer health index, diagnosis, risk and priority score;
- engineering maintenance recommendation;
- timestamped DGA gas-history visualisation;
- trend status, dominant rising gas and rate of increase;
- diagnostic confidence and engineering-use cautions.

The included four-transformer fleet is **synthetic demonstration data**. It is intended to exercise the software workflow and is not field-validation evidence.

## Engineering methodology

### 1. Longitudinal DGA trend analysis

For each gas, the extension calculates change over elapsed time and expresses the result in **ppm/month**. With at least three observations it can also calculate an acceleration signal. A dominant rising gas is surfaced as concise engineering evidence.

Trend labels such as `RAPID DETERIORATION` and `DETERIORATING` use **project-defined heuristic thresholds**. They are not IEC/IEEE alarm limits and require validation before operational use.

### 2. Transparent health and risk scoring

The extension converts multiple signals into an interpretable risk score:

```text
Risk score =
    65% fault-severity contribution
  + 25% DGA-trend contribution
  + 10% diagnostic-uncertainty contribution

Health index = 100 - risk score
```

Risk categories are then mapped to LOW, MODERATE, HIGH or CRITICAL bands. Fault-severity values, weights and category boundaries are deliberately visible in code so they can be reviewed, sensitivity-tested and replaced with validated organisational rules.

### 3. Predictive-maintenance assessment

`assess_history(...)` combines:

- the latest transformer gas state;
- longitudinal DGA behaviour;
- fault diagnosis and confidence;
- health/risk scoring;
- maintenance priority and an engineering recommendation.

The diagnostic interface is injectable through `assess_with_model(...)`, allowing the existing calibrated model, a future API or a test double to be connected without tightly coupling the maintenance logic to one model implementation.

### 4. Fleet prioritisation

Fleet ranking starts with the transparent risk score and applies small escalation factors for rapid deterioration and selected higher-severity diagnosis classes. The score is capped at 100 and is used as a **decision-support ranking**, not as a probability of failure.

## Upstream DGA/ML foundation

The original project by Ankit Raj includes:

- Key Gas, IEC-ratio and Duval Triangle classical diagnostic methods;
- physics-informed DGA feature engineering;
- calibrated XGBoost fault classification;
- Random Forest comparison;
- SHAP explainability;
- seven diagnostic classes: `Normal`, `PD`, `D1`, `D2`, `T1`, `T2`, `T3`;
- FAISS + sentence-transformer retrieval;
- an LLM diagnostic agent;
- sensor simulation and a Flask-based dashboard.

The upstream README reports **80.0% accuracy on its 70-row sealed test set** for the calibrated XGBoost model, compared with **57.1%** for its Duval Triangle implementation. Those are **upstream benchmark results** and should not be interpreted as validation of the predictive-maintenance extension.

## Run the predictive-maintenance dashboard

Clone this fork and switch to the development branch:

```bash
git clone https://github.com/arqam3025/transformer-health-dga.git
cd transformer-health-dga
git switch feature/predictive-maintenance-extension
```

Install the lightweight dashboard dependencies:

```bash
python -m pip install -r requirements-dashboard.txt
```

Launch:

```bash
python -m streamlit run dashboard.py
```

The terminal will display the local address for the running Streamlit application.

## Testing and CI

Run the extension tests locally with:

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```

GitHub Actions runs the same suite across **Python 3.10, 3.11 and 3.12**. The workflow is defined in `.github/workflows/predictive-maintenance-ci.yml`.

## Repository map

```text
transformer-health-dga/
├── dashboard.py                         # Streamlit asset-health dashboard [extension]
├── requirements-dashboard.txt           # Dashboard dependencies [extension]
├── src/
│   ├── dga_trend_analysis.py            # Longitudinal DGA trends [extension]
│   ├── health_index.py                  # Health/risk engine [extension]
│   ├── predictive_maintenance.py        # Integrated assessment [extension]
│   ├── fleet_prioritization.py          # Fleet ranking [extension]
│   ├── predict.py                       # Existing DGA prediction layer [upstream]
│   ├── classical/                       # Classical DGA diagnostics [upstream]
│   └── ...                              # RAG, agent and simulator modules [upstream]
├── tests/
│   ├── test_dga_trend_analysis.py       # [extension]
│   ├── test_health_index.py             # [extension]
│   ├── test_predictive_maintenance.py   # [extension]
│   └── test_fleet_prioritization.py     # [extension]
├── .github/workflows/
│   └── predictive-maintenance-ci.yml    # Multi-version CI [extension]
├── app/                                 # Original Flask dashboard [upstream]
├── notebooks/                           # Original ML pipeline [upstream]
├── models/                              # Original model artefacts [upstream]
└── LICENSE                              # Original MIT license retained
```

## Limitations and responsible engineering use

This repository is a **research/portfolio prototype**, not a certified transformer protection or maintenance system.

The predictive-maintenance health score, trend thresholds, risk weights and fleet escalation factors are transparent engineering heuristics developed for this extension; they are **not IEC/IEEE standard limits**. The included longitudinal fleet data are synthetic. No remaining-useful-life accuracy or failure-time prediction is claimed. No field validation has been performed for the extension.

Operational deployment would require, at minimum, longitudinal field DGA data, data-quality controls, sensitivity/uncertainty analysis, validation against engineering outcomes, organisation-specific maintenance rules and review by appropriately qualified engineers. Maintenance decisions should use applicable standards, test evidence and engineering judgement rather than this software alone.

The upstream project separately documents limitations of its classifier, including its curated test set, rare T2 samples and lack of longitudinal DGA data.

## Standards context

The upstream diagnostic work references:

- IEC 60599:2022 — interpretation of dissolved and free gases in mineral-oil-filled electrical equipment;
- IEEE C57.104-2019 — interpretation of gases generated in mineral-oil-immersed transformers;
- CIGRE Technical Brochure 761 — DGA interpretation.

References to these documents describe the diagnostic context. They do **not** imply that the extension's custom health-index weights or deterioration thresholds are standardised by those publications.

## Extension authorship

**Predictive-maintenance extension:** Raja Arqam Abdullah  
GitHub: [arqam3025](https://github.com/arqam3025)

Extension scope: longitudinal DGA trend analysis, transformer health/risk assessment, predictive-maintenance integration, fleet prioritisation, Streamlit asset-health dashboard, automated tests and CI integration.

## Upstream attribution

**Original project:** *Intelligent Transformer Health Monitoring using DGA & ML*  
**Original author:** Ankit Raj (GitHub: [AR0714](https://github.com/AR0714))  
**Upstream repository:** [AR0714/transformer-health-dga](https://github.com/AR0714/transformer-health-dga)

This fork retains the upstream MIT License and original copyright notice. See `LICENSE` for the license text.

---

### Suggested next research steps

For stronger research validity, future work should prioritise real longitudinal DGA histories, sensitivity analysis of the health-index parameters, time-aware validation, uncertainty calibration at the maintenance-decision level, and comparison of ranking decisions against observed inspection or failure outcomes.
