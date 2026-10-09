# Technical evolution and reproducibility notes

The current implementation uses a deterministic synthetic-behavior generator and a relational analytics pipeline.

Key changes relative to the early prototype:
- behavior-linked engagement, buffering, support propensity and churn risk
- heterogeneous active lifespan so retention is not degenerate
- D1/D7/D30 rolling retention on a common mature cohort
- plan-level monetization without subscriber duplication from recurring payments
- richer churn signal for a meaningful but explicitly synthetic classification task
- automated data-quality checks

Final deterministic run (NumPy seed 42):
- D1/D7/D30 rolling retention: 97.52% / 83.21% / 50.90%
- Churn ROC-AUC: 0.8876
- Churn recall: 0.8226
- Churn F1: 0.6254

These results describe the synthetic simulation only.
