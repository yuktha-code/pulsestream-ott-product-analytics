-- PulseStream reusable analytical SQL
-- Run against data/pulsestream.db after `python run_pipeline.py`.

-- 1) Platform watch summary
SELECT
    COUNT(*) AS watch_sessions,
    COUNT(DISTINCT user_id) AS active_users,
    ROUND(AVG(watch_minutes), 2) AS avg_watch_minutes,
    ROUND(AVG(completion_rate), 4) AS avg_completion_rate,
    ROUND(AVG(buffering_ratio), 4) AS avg_buffering_ratio
FROM watch_sessions;

-- 2) Recommendation funnel
SELECT
    COUNT(*) AS impressions,
    SUM(is_clicked) AS clicks,
    SUM(is_played) AS plays,
    ROUND(1.0 * SUM(is_clicked) / COUNT(*), 4) AS ctr,
    ROUND(1.0 * SUM(is_played) / COUNT(*), 4) AS impression_to_play
FROM recommendation_impressions;

-- 3) Search funnel
SELECT
    COUNT(*) AS searches,
    SUM(is_clicked) AS clicks,
    SUM(is_played) AS plays,
    ROUND(1.0 * SUM(is_clicked) / COUNT(*), 4) AS search_ctr,
    ROUND(1.0 * SUM(is_played) / COUNT(*), 4) AS search_to_play
FROM search_events;

-- 4) Monthly DAU/MAU stickiness
WITH monthly_users AS (
    SELECT SUBSTR(started_at, 1, 7) AS month,
           COUNT(DISTINCT user_id) AS mau
    FROM watch_sessions
    GROUP BY 1
),
daily_users AS (
    SELECT SUBSTR(started_at, 1, 7) AS month,
           DATE(started_at) AS date,
           COUNT(DISTINCT user_id) AS dau
    FROM watch_sessions
    GROUP BY 1, 2
)
SELECT m.month, m.mau,
       ROUND(AVG(d.dau), 2) AS avg_dau,
       ROUND(1.0 * AVG(d.dau) / m.mau, 4) AS dau_mau
FROM monthly_users m
JOIN daily_users d USING (month)
GROUP BY m.month, m.mau
ORDER BY m.month;

-- 5) Plan monetization + churn (aggregate payments before joining)
WITH payment_by_subscription AS (
    SELECT subscription_id,
           SUM(CASE WHEN payment_status = 'Success' THEN amount_inr ELSE 0 END) AS revenue_inr
    FROM payments
    GROUP BY subscription_id
)
SELECT s.plan,
       COUNT(*) AS subscribers,
       ROUND(SUM(COALESCE(p.revenue_inr, 0)), 2) AS revenue_inr,
       ROUND(1.0 * SUM(s.is_churned) / COUNT(*), 4) AS churn_rate
FROM subscriptions s
LEFT JOIN payment_by_subscription p
  ON p.subscription_id = s.subscription_id
GROUP BY s.plan
ORDER BY revenue_inr DESC;

-- 6) Paid conversion by acquisition channel
SELECT u.acquisition_channel,
       COUNT(DISTINCT u.user_id) AS users,
       COUNT(DISTINCT CASE WHEN s.monthly_price_inr > 0 THEN u.user_id END) AS paid_users,
       ROUND(
           1.0 * COUNT(DISTINCT CASE WHEN s.monthly_price_inr > 0 THEN u.user_id END)
           / COUNT(DISTINCT u.user_id), 4
       ) AS paid_conversion
FROM users u
JOIN subscriptions s ON s.user_id = u.user_id
GROUP BY u.acquisition_channel
ORDER BY paid_conversion DESC;

-- 7) Content efficiency proxy
SELECT c.content_id, c.title, c.content_type, c.genre, c.language,
       c.licensing_cost_index,
       COUNT(*) AS starts,
       ROUND(SUM(w.watch_minutes), 2) AS watch_minutes,
       ROUND(AVG(w.completion_rate), 4) AS avg_completion_rate,
       ROUND(SUM(w.watch_minutes) / NULLIF(c.licensing_cost_index, 0), 2)
           AS watch_minutes_per_cost_index
FROM watch_sessions w
JOIN content c ON c.content_id = w.content_id
GROUP BY c.content_id, c.title, c.content_type, c.genre, c.language, c.licensing_cost_index
ORDER BY watch_minutes_per_cost_index DESC
LIMIT 25;

-- 8) Engagement and support profile by churn status
WITH watch_user AS (
    SELECT user_id,
           COUNT(*) AS sessions,
           SUM(watch_minutes) AS watch_minutes,
           AVG(completion_rate) AS completion_rate,
           AVG(buffering_ratio) AS buffering_ratio
    FROM watch_sessions
    GROUP BY user_id
),
support_user AS (
    SELECT user_id, COUNT(*) AS support_tickets
    FROM support_events
    GROUP BY user_id
)
SELECT s.is_churned,
       COUNT(*) AS users,
       ROUND(AVG(COALESCE(w.sessions, 0)), 2) AS avg_sessions,
       ROUND(AVG(COALESCE(w.watch_minutes, 0)), 2) AS avg_watch_minutes,
       ROUND(AVG(COALESCE(w.completion_rate, 0)), 4) AS avg_completion_rate,
       ROUND(AVG(COALESCE(w.buffering_ratio, 0)), 4) AS avg_buffering_ratio,
       ROUND(AVG(COALESCE(sp.support_tickets, 0)), 2) AS avg_support_tickets
FROM subscriptions s
LEFT JOIN watch_user w ON w.user_id = s.user_id
LEFT JOIN support_user sp ON sp.user_id = s.user_id
GROUP BY s.is_churned;
