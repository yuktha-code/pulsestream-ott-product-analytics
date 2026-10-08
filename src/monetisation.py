from __future__ import annotations

import sqlite3
from pathlib import Path
import pandas as pd


def run_monetisation(db_path="data/pulsestream.db"):
    conn = sqlite3.connect(db_path)

    # Aggregate payments first to prevent a subscriber being duplicated by
    # multiple monthly payment rows when calculating churn.
    plan = pd.read_sql_query("""
        WITH payment_by_subscription AS (
            SELECT
                subscription_id,
                SUM(CASE WHEN payment_status='Success'
                         THEN amount_inr ELSE 0 END) AS revenue_inr
            FROM payments
            GROUP BY subscription_id
        )
        SELECT
            s.plan,
            COUNT(*) AS subscribers,
            ROUND(SUM(COALESCE(p.revenue_inr, 0)), 2) AS revenue_inr,
            ROUND(1.0 * SUM(s.is_churned) / COUNT(*), 4) AS churn_rate
        FROM subscriptions s
        LEFT JOIN payment_by_subscription p
          ON p.subscription_id = s.subscription_id
        GROUP BY s.plan
        ORDER BY revenue_inr DESC
    """, conn)

    channel = pd.read_sql_query("""
        SELECT
            u.acquisition_channel,
            COUNT(DISTINCT u.user_id) AS users,
            COUNT(DISTINCT CASE
                WHEN s.monthly_price_inr > 0 THEN u.user_id END
            ) AS paid_users,
            ROUND(
                1.0 * COUNT(DISTINCT CASE
                    WHEN s.monthly_price_inr > 0 THEN u.user_id END
                ) / COUNT(DISTINCT u.user_id),
                4
            ) AS paid_conversion
        FROM users u
        JOIN subscriptions s ON s.user_id = u.user_id
        GROUP BY u.acquisition_channel
        ORDER BY paid_conversion DESC
    """, conn)

    conn.close()
    Path("results").mkdir(exist_ok=True)
    plan.to_csv("results/monetisation_by_plan.csv", index=False)
    channel.to_csv("results/conversion_by_channel.csv", index=False)
    return plan, channel


if __name__ == "__main__":
    plan, channel = run_monetisation()
    print(plan.to_string(index=False))
    print()
    print(channel.to_string(index=False))
