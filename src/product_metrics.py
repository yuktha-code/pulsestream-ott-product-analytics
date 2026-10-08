from __future__ import annotations

import json
import sqlite3
from pathlib import Path
import pandas as pd


def run_metrics(db_path="data/pulsestream.db"):
    conn = sqlite3.connect(db_path)

    summary = pd.read_sql_query("""
        SELECT
            COUNT(DISTINCT user_id) AS total_users,
            COUNT(*) AS total_watch_sessions,
            ROUND(AVG(watch_minutes), 2) AS avg_watch_minutes,
            ROUND(AVG(completion_rate), 4) AS avg_completion_rate,
            ROUND(AVG(buffering_ratio), 4) AS avg_buffering_ratio
        FROM watch_sessions
    """, conn).iloc[0].to_dict()

    rec = pd.read_sql_query("""
        SELECT
            COUNT(*) AS impressions,
            SUM(is_clicked) AS clicks,
            SUM(is_played) AS plays,
            ROUND(1.0 * SUM(is_clicked) / COUNT(*), 4) AS ctr,
            ROUND(1.0 * SUM(is_played) / COUNT(*), 4) AS play_rate
        FROM recommendation_impressions
    """, conn).iloc[0].to_dict()

    search = pd.read_sql_query("""
        SELECT
            COUNT(*) AS searches,
            SUM(is_clicked) AS clicks,
            SUM(is_played) AS plays,
            ROUND(1.0 * SUM(is_clicked) / COUNT(*), 4) AS search_ctr,
            ROUND(1.0 * SUM(is_played) / COUNT(*), 4) AS search_to_play
        FROM search_events
    """, conn).iloc[0].to_dict()

    revenue = pd.read_sql_query("""
        SELECT
            ROUND(SUM(
                CASE WHEN payment_status='Success'
                THEN amount_inr ELSE 0 END
            ), 2) AS successful_revenue_inr,
            COUNT(DISTINCT CASE
                WHEN payment_status='Success' THEN user_id END
            ) AS paying_users
        FROM payments
    """, conn).iloc[0].to_dict()
    revenue["arppu_inr"] = round(
        revenue["successful_revenue_inr"] / revenue["paying_users"], 2
    )

    # Daily active users.
    daily = pd.read_sql_query("""
        SELECT
            DATE(started_at) AS date,
            COUNT(DISTINCT user_id) AS dau
        FROM watch_sessions
        GROUP BY DATE(started_at)
        ORDER BY date
    """, conn)

    # MAU and average DAU for each month; stickiness = avg DAU / MAU.
    monthly = pd.read_sql_query("""
        WITH monthly_users AS (
            SELECT
                SUBSTR(started_at,1,7) AS month,
                COUNT(DISTINCT user_id) AS mau
            FROM watch_sessions
            GROUP BY SUBSTR(started_at,1,7)
        ),
        daily_users AS (
            SELECT
                SUBSTR(started_at,1,7) AS month,
                DATE(started_at) AS date,
                COUNT(DISTINCT user_id) AS dau
            FROM watch_sessions
            GROUP BY SUBSTR(started_at,1,7), DATE(started_at)
        )
        SELECT
            m.month,
            m.mau,
            ROUND(AVG(d.dau), 2) AS avg_dau,
            ROUND(1.0 * AVG(d.dau) / m.mau, 4) AS dau_mau_stickiness
        FROM monthly_users m
        JOIN daily_users d ON d.month = m.month
        GROUP BY m.month, m.mau
        ORDER BY m.month
    """, conn)

    churn = pd.read_sql_query("""
        SELECT
            plan,
            COUNT(*) AS subscribers,
            SUM(is_churned) AS churned,
            ROUND(1.0 * SUM(is_churned) / COUNT(*), 4) AS churn_rate
        FROM subscriptions
        GROUP BY plan
        ORDER BY churn_rate DESC
    """, conn)

    Path("results").mkdir(exist_ok=True)
    daily.to_csv("results/daily_active_users.csv", index=False)
    monthly.to_csv("results/monthly_stickiness.csv", index=False)
    churn.to_csv("results/churn_by_plan.csv", index=False)

    out = {
        "summary": summary,
        "recommendation_funnel": rec,
        "search_funnel": search,
        "revenue": revenue,
        "stickiness": {
            "mean_dau_mau": float(monthly["dau_mau_stickiness"].mean()),
            "latest_month_dau_mau": float(
                monthly.iloc[-1]["dau_mau_stickiness"]
            ),
        },
    }

    with open("results/kpi_summary.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    conn.close()
    return out


if __name__ == "__main__":
    print(json.dumps(run_metrics(), indent=2))
