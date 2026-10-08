import sqlite3
from pathlib import Path
import pandas as pd

def run_content_metrics(db_path="data/pulsestream.db"):
    conn=sqlite3.connect(db_path)
    df=pd.read_sql_query("""
    SELECT c.content_id,c.title,c.content_type,c.genre,c.language,c.licensing_cost_index,
           COUNT(w.session_id) starts,
           ROUND(SUM(w.watch_minutes),2) watch_minutes,
           ROUND(AVG(w.completion_rate),4) avg_completion_rate,
           ROUND(SUM(w.watch_minutes)/NULLIF(c.licensing_cost_index,0),2) watch_minutes_per_cost_index
    FROM content c
    LEFT JOIN watch_sessions w ON w.content_id=c.content_id
    GROUP BY c.content_id,c.title,c.content_type,c.genre,c.language,c.licensing_cost_index
    ORDER BY watch_minutes_per_cost_index DESC
    """,conn)
    conn.close()
    Path("results").mkdir(exist_ok=True)
    df.to_csv("results/content_roi_proxy.csv",index=False)
    return df

if __name__=="__main__":
    print(run_content_metrics().head(20).to_string(index=False))
