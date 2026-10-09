# PulseStream — OTT Engagement, Retention & Monetization Analytics

PulseStream is an end-to-end OTT product-analytics project built with **Python, SQL, SQLite and scikit-learn**. It simulates a joined streaming-platform warehouse, computes engagement/search/recommendation/retention/monetization KPIs, trains a churn classifier, ranks content-efficiency proxies and runs automated data-quality checks.

> **Data provenance:** all user-level data in this repository is synthetic and generated locally with NumPy seed `42`. This project does **not** use or claim access to JioHotstar, Disney+ Hotstar, Netflix, Prime Video or any other proprietary streaming-platform data.

## Why this project

OTT analytics requires multiple event streams to be interpreted together: watch behavior, search, recommendations, subscriptions, payments, devices and support interactions. Public datasets rarely provide all of these at a consistent user-level grain, so PulseStream generates a reproducible synthetic warehouse and focuses on the analytics workflow rather than pretending to have proprietary customer data.

## Dataset / warehouse scale

| Table | Rows |
|---|---:|
| Users | 10,000 |
| Content titles | 300 |
| Subscriptions | 10,000 |
| Devices | 10,000 |
| Watch sessions | 160,000 |
| Search events | 45,000 |
| Recommendation impressions | 120,000 |
| Payments | 43,010 |
| Support events | 8,000 |

The SQLite warehouse enforces primary/foreign-key relationships and indexes high-use event paths such as `(user_id, started_at)` for watch sessions.

## Final reproducible results

The current pipeline run produces:

- Recommendation CTR: **15.18%**
- Recommendation play rate: **11.45%**
- Search CTR: **58.92%**
- Search-to-play: **42.57%**
- Mean DAU/MAU stickiness: **13.91%**
- Successful synthetic revenue: **INR 13,308,967**
- Paying users: **7,167**
- ARPPU: **INR 1,856.98**
- Rolling retention: **D1 97.52% / D7 83.21% / D30 50.90%**
- Churn model: **ROC-AUC 0.888 / churn recall 82.3% / F1 0.625** on **2,500 test users**

These are metrics from the deterministic **synthetic simulation**, not real-world OTT benchmarks.

## Analytics workflow

1. **Synthetic data generation** — creates behavior-linked user engagement, buffering, support propensity, plan choice, active lifespan and churn risk.
2. **Warehouse build** — loads CSVs into SQLite using the relational schema in `sql/schema.sql`.
3. **Product KPIs** — DAU, DAU/MAU, watch/completion/buffering summaries, recommendation and search funnels, revenue and ARPPU.
4. **Retention & cohorts** — D1/D7/D30 rolling retention on a common mature cohort plus monthly cohort tables.
5. **Churn modeling** — logistic regression with numerical scaling, categorical one-hot encoding, class balancing and a stratified holdout.
6. **Content economics** — title-level starts, watch minutes, completion and a watch-minutes-per-licensing-cost-index proxy.
7. **Monetization analysis** — revenue/churn by plan and paid conversion by acquisition channel.
8. **Quality checks** — validates retention monotonicity/range, churn AUC sanity, relational integrity and expected row counts.

## Churn model

Features include:

- subscription plan and monthly price
- tenure
- city tier and acquisition channel
- session count and total watch minutes
- average completion rate
- average buffering ratio
- support-ticket count

The model is a scikit-learn pipeline with `StandardScaler`, `OneHotEncoder` and class-balanced `LogisticRegression`. The holdout is 25% of users with stratification by churn label.

## Project structure

```text
PulseStream/
├── README.md
├── DATA_SOURCES.md
├── CHANGELOG.md
├── requirements.txt
├── run_pipeline.py
├── data/                  # generated locally; CSV/DB ignored by Git
├── results/               # reproducible output summaries committed
├── sql/
│   ├── schema.sql
│   └── analytics.sql
├── src/
│   ├── generate_ott_data.py
│   ├── build_warehouse.py
│   ├── product_metrics.py
│   ├── cohort_analysis.py
│   ├── churn_analysis.py
│   ├── content_metrics.py
│   ├── monetisation.py
│   └── quality_checks.py
├── dashboard/
└── notebooks/
```

## Run locally

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_pipeline.py
```

Then inspect:

```powershell
Get-Content .\results\kpi_summary.json
Get-Content .\results\churn_model_metrics.json
Get-Content .\results\d1_d7_d30_rolling_retention.csv
Get-Content .\results\monetisation_by_plan.csv
```

## Data integrity and reproducibility

- Fixed NumPy seed: `42`
- Explicit table grain and PK/FK schema
- Generated raw CSVs and local SQLite DB are ignored by Git
- Automated quality checks fail the pipeline if retention is invalid, churn AUC is outside a sensible range, foreign-key violations exist, or expected table counts are wrong
- Published metrics should be quoted only from a successful pipeline run


## Continuous integration

The GitHub Actions workflow runs the full deterministic pipeline on Python 3.11 and then executes three post-run smoke tests. These check output quality flags, simulated event-table counts, and held-out churn-model metric bounds. Passing CI indicates that this synthetic demonstration remains reproducible; it does not establish real-world model performance.

## Limitations

- Synthetic behavior is intentionally structured, so model performance is **not** evidence of production churn-prediction performance.
- The churn split is a stratified user holdout, not a future temporal deployment test.
- `licensing_cost_index` is a simulated relative cost proxy, not a real content-rights price.
- The project demonstrates product-analytics methodology and reproducibility; production systems would require real event instrumentation, privacy controls, drift monitoring, experimentation and causal validation.
