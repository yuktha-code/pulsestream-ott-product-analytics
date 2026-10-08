import json, sqlite3
from pathlib import Path
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def run_churn_model(db_path="data/pulsestream.db"):
    conn=sqlite3.connect(db_path)
    df=pd.read_sql_query("""
    SELECT s.user_id,s.plan,s.monthly_price_inr,s.tenure_days,s.is_churned,
           u.city_tier,u.acquisition_channel,
           COALESCE(w.session_count,0) session_count,
           COALESCE(w.total_watch_minutes,0) total_watch_minutes,
           COALESCE(w.avg_completion_rate,0) avg_completion_rate,
           COALESCE(w.avg_buffering_ratio,0) avg_buffering_ratio,
           COALESCE(sp.support_tickets,0) support_tickets
    FROM subscriptions s
    JOIN users u ON u.user_id=s.user_id
    LEFT JOIN (
        SELECT user_id,COUNT(*) session_count,SUM(watch_minutes) total_watch_minutes,
               AVG(completion_rate) avg_completion_rate,AVG(buffering_ratio) avg_buffering_ratio
        FROM watch_sessions GROUP BY user_id
    ) w ON w.user_id=s.user_id
    LEFT JOIN (
        SELECT user_id,COUNT(*) support_tickets FROM support_events GROUP BY user_id
    ) sp ON sp.user_id=s.user_id
    """,conn)
    conn.close()

    y=df["is_churned"].astype(int)
    X=df.drop(columns=["user_id","is_churned"])
    cat=["plan","city_tier","acquisition_channel"]
    num=[c for c in X.columns if c not in cat]
    pre=ColumnTransformer([("num",StandardScaler(),num),("cat",OneHotEncoder(handle_unknown="ignore"),cat)])
    pipe=Pipeline([("pre",pre),("clf",LogisticRegression(max_iter=1000,class_weight="balanced"))])
    Xtr,Xte,ytr,yte=train_test_split(X,y,test_size=.25,random_state=42,stratify=y)
    pipe.fit(Xtr,ytr)
    prob=pipe.predict_proba(Xte)[:,1]
    pred=(prob>=.5).astype(int)
    rep=classification_report(yte,pred,output_dict=True,zero_division=0)
    out={"roc_auc":float(roc_auc_score(yte,prob)),"test_rows":int(len(yte)),
         "positive_rate":float(yte.mean()),"precision_churn":float(rep["1"]["precision"]),
         "recall_churn":float(rep["1"]["recall"]),"f1_churn":float(rep["1"]["f1-score"])}
    Path("results/churn_model_metrics.json").write_text(json.dumps(out,indent=2),encoding="utf-8")
    return out

if __name__=="__main__":
    print(json.dumps(run_churn_model(),indent=2))
