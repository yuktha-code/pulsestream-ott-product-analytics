# Data Sources and Provenance

PulseStream uses fully synthetic data generated locally by `src/generate_ott_data.py`.

No proprietary streaming-platform data is used.

## Why synthetic data

User-level OTT watch histories, recommendation impressions, subscription payments,
support events and churn labels are commercially sensitive and generally unavailable
as an open, joined relational dataset. A synthetic warehouse allows the full analytics
workflow to be reproduced without implying access to private customer data.

## Reproducibility

The generator uses NumPy random seed `42`.

The generated warehouse contains:
- 10,000 users
- 300 content titles
- 160,000 watch sessions
- 45,000 search events
- 120,000 recommendation impressions
- subscription records
- recurring payment records
- device records
- support events

Generated KPIs describe the synthetic simulation only. They must not be represented
as real JioHotstar, Disney+ Hotstar, Netflix, Prime Video, or other platform metrics.
