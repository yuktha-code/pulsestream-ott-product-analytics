from src.generate_ott_data import generate_all
from src.build_warehouse import build_database
from src.product_metrics import run_metrics
from src.cohort_analysis import run_cohorts
from src.churn_analysis import run_churn_model
from src.content_metrics import run_content_metrics
from src.monetisation import run_monetisation
from src.quality_checks import run_quality_checks

if __name__ == "__main__":
    print("1/8 Generating behaviour-linked synthetic OTT data...")
    tables = generate_all()
    for k, v in tables.items():
        print(f"  {k}: {len(v):,} rows")

    print("\n2/8 Building warehouse...")
    conn = build_database()
    conn.close()

    print("\n3/8 Product KPIs...")
    print(run_metrics())

    print("\n4/8 Rolling retention + monthly cohorts...")
    retention, _ = run_cohorts()
    print(retention.to_string(index=False))

    print("\n5/8 Churn model...")
    print(run_churn_model())

    print("\n6/8 Content economics...")
    print(run_content_metrics().head(10).to_string(index=False))

    print("\n7/8 Monetisation...")
    plan, channel = run_monetisation()
    print(plan.to_string(index=False))
    print(channel.to_string(index=False))

    print("\n8/8 Quality checks...")
    run_quality_checks()

    print("\nDone. See results/ for outputs.")
