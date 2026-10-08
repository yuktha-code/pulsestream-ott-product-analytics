from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

RNG = np.random.default_rng(42)
OBS_END = pd.Timestamp("2026-09-30")

PLAN_PRICE = {"Free": 0, "Mobile": 149, "Super": 299, "Premium": 499}
PLAN_ENGAGEMENT = {"Free": -0.05, "Mobile": 0.00, "Super": 0.05, "Premium": 0.08}
PLAN_CHURN_LOGIT = {"Free": 0.50, "Mobile": 0.25, "Super": -0.15, "Premium": -0.35}


def random_dates(start: str, end: str, n: int) -> pd.DatetimeIndex:
    start = pd.Timestamp(start)
    end = pd.Timestamp(end)
    offsets = RNG.integers(0, (end - start).days + 1, n)
    return start + pd.to_timedelta(offsets, unit="D")


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def generate_all(out_dir="data"):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # 1) Users + latent behavioural traits
    # ------------------------------------------------------------------
    n_users = 10_000
    users = pd.DataFrame({
        "user_id": np.arange(1, n_users + 1),
        "signup_date": random_dates("2025-01-01", "2026-06-30", n_users).date,
        "city_tier": RNG.choice(["Tier 1", "Tier 2", "Tier 3"], n_users, p=[0.45, 0.35, 0.20]),
        "acquisition_channel": RNG.choice(
            ["Organic", "Paid Social", "Search", "Referral", "Partner"],
            n_users,
            p=[0.25, 0.20, 0.20, 0.18, 0.17],
        ),
        "age_band": RNG.choice(["18-24", "25-34", "35-44", "45+"], n_users, p=[0.28, 0.39, 0.21, 0.12]),
    })

    plans = RNG.choice(["Free", "Mobile", "Super", "Premium"], n_users, p=[0.28, 0.20, 0.30, 0.22])

    latent_engagement = RNG.beta(2.2, 2.2, n_users)
    latent_engagement += np.array([PLAN_ENGAGEMENT[p] for p in plans])
    latent_engagement = np.clip(latent_engagement, 0.02, 0.98)

    base_buffering = RNG.gamma(1.2, 0.012, n_users) + (1.0 - latent_engagement) * 0.012
    base_buffering = np.clip(base_buffering, 0.002, 0.15)

    support_propensity = RNG.beta(1.5, 5.0, n_users) + (1.0 - latent_engagement) * 0.20
    support_propensity = np.clip(support_propensity, 0.0, 1.0)

    plan_risk = np.array([PLAN_CHURN_LOGIT[p] for p in plans])
    churn_logit = (
        -1.60
        + plan_risk
        + 2.80 * (0.50 - latent_engagement)
        + 10.0 * (base_buffering - 0.02)
        + 0.80 * (support_propensity - 0.25)
    )
    churn_prob = sigmoid(churn_logit)
    churned = RNG.binomial(1, churn_prob)

    # Active lifespan is deliberately tied to engagement/churn so that
    # retention and churn analytics have meaningful structure.
    churn_span_scale = 7 + 25 * latent_engagement
    retained_span_scale = 20 + 80 * latent_engagement
    raw_span = np.where(
        churned == 1,
        RNG.exponential(churn_span_scale),
        RNG.exponential(retained_span_scale),
    ).astype(int)

    first_watch = (
        pd.to_datetime(users["signup_date"])
        + pd.to_timedelta(RNG.integers(0, 5, n_users), unit="D")
    )
    available_days = np.maximum(
        0, (OBS_END - first_watch).dt.days.to_numpy()
    )
    active_span_days = np.minimum(raw_span, available_days)

    subscriptions = pd.DataFrame({
        "subscription_id": np.arange(1, n_users + 1),
        "user_id": users["user_id"],
        "plan": plans,
        "monthly_price_inr": [PLAN_PRICE[p] for p in plans],
        "start_date": pd.to_datetime(users["signup_date"]) + pd.to_timedelta(RNG.integers(0, 8, n_users), unit="D"),
        "is_churned": churned,
        "tenure_days": np.maximum(1, active_span_days),
    })

    # ------------------------------------------------------------------
    # 2) Content catalogue
    # ------------------------------------------------------------------
    n_content = 300
    ctype = RNG.choice(["Movie", "Series", "Sports"], n_content, p=[0.48, 0.42, 0.10])
    content = pd.DataFrame({
        "content_id": np.arange(1, n_content + 1),
        "title": [f"Title_{i:04d}" for i in range(1, n_content + 1)],
        "content_type": ctype,
        "genre": RNG.choice(["Drama", "Comedy", "Action", "Crime", "Romance", "Sports", "Kids", "Documentary"], n_content),
        "language": RNG.choice(["Hindi", "English", "Telugu", "Tamil", "Malayalam", "Kannada", "Bengali"], n_content),
        "release_year": RNG.integers(2012, 2027, n_content),
        "duration_min": np.where(
            ctype == "Movie",
            RNG.integers(85, 170, n_content),
            np.where(ctype == "Sports", RNG.integers(90, 240, n_content), RNG.integers(25, 60, n_content)),
        ),
        "licensing_cost_index": np.round(RNG.lognormal(2.3, 0.55, n_content), 2),
    })

    # ------------------------------------------------------------------
    # 3) Watch sessions: exactly 160,000 rows
    # ------------------------------------------------------------------
    n_sessions = 160_000

    # Every user gets a first session. Users with active_span > 0 also get
    # a guaranteed later session at their simulated active-lifespan edge.
    base_counts = np.ones(n_users, dtype=int)
    second_mask = active_span_days > 0
    base_counts[second_mask] += 1

    remaining = n_sessions - int(base_counts.sum())
    intensity = (
        0.15
        + 1.60 * latent_engagement
        + np.array([{"Free": 0.00, "Mobile": 0.05, "Super": 0.12, "Premium": 0.18}[p] for p in plans])
    )
    intensity = np.maximum(intensity, 0.01)
    extra_counts = RNG.multinomial(remaining, intensity / intensity.sum())
    session_counts = base_counts + extra_counts

    user_ids = np.repeat(np.arange(1, n_users + 1), session_counts)

    session_dates = []
    completion_values = []
    buffering_values = []

    for i in range(n_users):
        count = int(session_counts[i])
        span = int(active_span_days[i])

        offsets = [0]
        if count >= 2:
            offsets.append(span)

        if count > 2:
            if span <= 0:
                middle = np.zeros(count - 2, dtype=int)
            else:
                # Early-heavy but spread across the user's active lifespan.
                middle = np.floor(
                    RNG.beta(1.15, 1.85, count - 2) * span
                ).astype(int)
            offsets.extend(middle.tolist())

        offsets = np.array(offsets[:count], dtype=int)
        dates = first_watch.iloc[i] + pd.to_timedelta(offsets, unit="D")
        dates = dates + pd.to_timedelta(RNG.integers(0, 24 * 60, count), unit="m")
        session_dates.extend(dates.tolist())

        eng = latent_engagement[i]
        alpha = 1.3 + 4.2 * eng
        beta = 1.4 + 3.0 * (1.0 - eng)
        completion = np.clip(RNG.beta(alpha, beta, count), 0.01, 1.0)
        completion_values.extend(completion.tolist())

        buff = np.clip(
            base_buffering[i] + RNG.normal(0, 0.006, count),
            0.0,
            0.25,
        )
        buffering_values.extend(buff.tolist())

    content_ids = RNG.choice(content["content_id"].to_numpy(), n_sessions)
    duration = content.set_index("content_id").loc[content_ids, "duration_min"].to_numpy()
    completion_values = np.asarray(completion_values)
    buffering_values = np.asarray(buffering_values)

    watch_sessions = pd.DataFrame({
        "session_id": np.arange(1, n_sessions + 1),
        "user_id": user_ids,
        "content_id": content_ids,
        "started_at": pd.to_datetime(session_dates),
        "watch_minutes": np.maximum(1, (duration * completion_values).astype(int)),
        "completion_rate": np.round(completion_values, 4),
        "play_source": RNG.choice(
            ["Home", "Search", "Recommendation", "Continue Watching", "Deep Link"],
            n_sessions,
            p=[0.29, 0.17, 0.31, 0.18, 0.05],
        ),
        "buffering_ratio": np.round(buffering_values, 4),
    })

    # ------------------------------------------------------------------
    # 4) Search and recommendation events
    # ------------------------------------------------------------------
    user_weights = intensity / intensity.sum()

    n_search = 45_000
    search_users = RNG.choice(users["user_id"].to_numpy(), n_search, p=user_weights)
    search_click_prob = np.clip(0.42 + 0.28 * latent_engagement[search_users - 1], 0.05, 0.90)
    search_clicked = RNG.binomial(1, search_click_prob)
    search_play_prob = np.clip(0.55 + 0.28 * latent_engagement[search_users - 1], 0.05, 0.95)
    search_played = search_clicked * RNG.binomial(1, search_play_prob)
    search_events = pd.DataFrame({
        "search_id": np.arange(1, n_search + 1),
        "user_id": search_users,
        "searched_at": random_dates("2025-07-01", "2026-09-30", n_search),
        "is_clicked": search_clicked,
        "is_played": search_played,
    })

    n_rec = 120_000
    rec_users = RNG.choice(users["user_id"].to_numpy(), n_rec, p=user_weights)
    rec_ctr_prob = np.clip(0.08 + 0.12 * latent_engagement[rec_users - 1], 0.02, 0.35)
    rec_clicked = RNG.binomial(1, rec_ctr_prob)
    rec_play_prob = np.clip(0.60 + 0.25 * latent_engagement[rec_users - 1], 0.10, 0.95)
    rec_played = rec_clicked * RNG.binomial(1, rec_play_prob)
    recommendation_impressions = pd.DataFrame({
        "impression_id": np.arange(1, n_rec + 1),
        "user_id": rec_users,
        "content_id": RNG.choice(content["content_id"].to_numpy(), n_rec),
        "impressed_at": random_dates("2025-07-01", "2026-09-30", n_rec),
        "surface": RNG.choice(["Home", "Because You Watched", "Trending", "Sports Hub"], n_rec),
        "is_clicked": rec_clicked,
        "is_played": rec_played,
    })

    # ------------------------------------------------------------------
    # 5) Payments, support and devices
    # ------------------------------------------------------------------
    payments = []
    pid = 1
    for i, row in enumerate(subscriptions.itertuples(index=False)):
        if row.monthly_price_inr <= 0:
            continue

        if row.is_churned:
            months = max(1, min(12, int(np.ceil(active_span_days[i] / 30.0))))
        else:
            months = int(RNG.integers(4, 11))

        start = pd.Timestamp(row.start_date)
        for m in range(months):
            payments.append({
                "payment_id": pid,
                "user_id": int(row.user_id),
                "subscription_id": int(row.subscription_id),
                "payment_date": (start + pd.DateOffset(months=m)).date(),
                "amount_inr": float(row.monthly_price_inr),
                "payment_status": RNG.choice(["Success", "Failed", "Refunded"], p=[0.94, 0.04, 0.02]),
            })
            pid += 1
    payments = pd.DataFrame(payments)

    n_support = 8_000
    support_weights = 0.05 + support_propensity + 0.80 * churned
    support_weights = support_weights / support_weights.sum()
    support_users = RNG.choice(users["user_id"].to_numpy(), n_support, p=support_weights)
    support_events = pd.DataFrame({
        "support_event_id": np.arange(1, n_support + 1),
        "user_id": support_users,
        "created_at": random_dates("2025-07-01", "2026-09-30", n_support),
        "issue_type": RNG.choice(["Playback", "Payment", "Login", "Content", "Subscription"], n_support),
        "resolution_hours": np.round(
            np.clip(
                RNG.gamma(2.0, 4.0, n_support)
                + 5.0 * churned[support_users - 1],
                0.2,
                72,
            ),
            2,
        ),
    })

    devices = pd.DataFrame({
        "device_id": np.arange(1, n_users + 1),
        "user_id": users["user_id"],
        "device_type": RNG.choice(["Android", "iOS", "Web", "Smart TV"], n_users, p=[0.48, 0.18, 0.16, 0.18]),
    })

    tables = {
        "users": users,
        "content": content,
        "subscriptions": subscriptions,
        "devices": devices,
        "watch_sessions": watch_sessions,
        "search_events": search_events,
        "recommendation_impressions": recommendation_impressions,
        "payments": payments,
        "support_events": support_events,
    }

    for name, df in tables.items():
        df.to_csv(out / f"{name}.csv", index=False)

    return tables


if __name__ == "__main__":
    for name, df in generate_all().items():
        print(f"{name}: {len(df):,} rows")
