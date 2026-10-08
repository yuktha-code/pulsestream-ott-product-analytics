from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd


def run_cohorts(db_path="data/pulsestream.db"):
    """
    Rolling retention on a common mature cohort.

    To keep D1, D7 and D30 comparable, only users whose first watch occurred at
    least 30 days before the end of the observation window are included.
    A user is retained at horizon H if they have any activity H or more days
    after their first watch.
    """
    conn = sqlite3.connect(db_path)
    sessions = pd.read_sql_query(
        "SELECT user_id, started_at FROM watch_sessions", conn
    )
    conn.close()

    sessions["started_at"] = pd.to_datetime(sessions["started_at"])
    first = sessions.groupby("user_id")["started_at"].min()
    last = sessions.groupby("user_id")["started_at"].max()

    obs_end = sessions["started_at"].max().normalize()
    mature_users = first[first <= obs_end - pd.Timedelta(days=30)].index

    first = first.loc[mature_users]
    last = last.loc[mature_users]
    max_day = (last.dt.normalize() - first.dt.normalize()).dt.days

    n = int(len(max_day))
    rows = []
    for horizon in [1, 7, 30]:
        retained = int((max_day >= horizon).sum())
        rows.append({
            "horizon_days": horizon,
            "eligible_users": n,
            "retained_users": retained,
            "rolling_retention_rate": retained / n if n else 0.0,
        })

    retention = pd.DataFrame(rows)

    # Monthly first-watch cohorts.
    first_df = first.rename("first_watch").reset_index()
    first_df["cohort_month"] = first_df["first_watch"].dt.to_period("M")

    activity = sessions[sessions["user_id"].isin(mature_users)].copy()
    activity["activity_month"] = activity["started_at"].dt.to_period("M")
    activity = activity[["user_id", "activity_month"]].drop_duplicates()

    ca = first_df[["user_id", "cohort_month"]].merge(
        activity, on="user_id", how="left"
    )
    ca["month_number"] = (
        (ca["activity_month"].dt.year - ca["cohort_month"].dt.year) * 12
        + (ca["activity_month"].dt.month - ca["cohort_month"].dt.month)
    )

    counts = (
        ca.groupby(["cohort_month", "month_number"])["user_id"]
        .nunique()
        .reset_index(name="active_users")
    )
    sizes = (
        counts[counts["month_number"] == 0][["cohort_month", "active_users"]]
        .rename(columns={"active_users": "cohort_size"})
    )
    counts = counts.merge(sizes, on="cohort_month", how="left")
    counts["retention_rate"] = counts["active_users"] / counts["cohort_size"]
    counts["cohort_month"] = counts["cohort_month"].astype(str)

    Path("results").mkdir(exist_ok=True)
    retention.to_csv(
        "results/d1_d7_d30_rolling_retention.csv", index=False
    )
    counts.to_csv("results/monthly_cohort_retention.csv", index=False)

    return retention, counts


if __name__ == "__main__":
    r, _ = run_cohorts()
    print(r.to_string(index=False))
