import sqlite3
from pathlib import Path
import pandas as pd

TABLES = ["users","content","subscriptions","devices","watch_sessions","search_events","recommendation_impressions","payments","support_events"]

def build_database(data_dir="data", db_path="data/pulsestream.db"):
    db = Path(db_path)
    if db.exists():
        db.unlink()
    conn = sqlite3.connect(db)
    conn.executescript(Path("sql/schema.sql").read_text(encoding="utf-8"))
    for table in TABLES:
        pd.read_csv(Path(data_dir)/f"{table}.csv").to_sql(table, conn, if_exists="append", index=False)
    conn.commit()
    return conn

if __name__ == "__main__":
    c = build_database()
    c.close()
    print("Built data/pulsestream.db")
