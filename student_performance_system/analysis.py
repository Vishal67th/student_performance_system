"""Analysis logic: metrics, grades, ranking, at-risk detection, clustering, prediction."""
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.linear_model import LinearRegression
from database import SUBJECTS

PASS_MARK = 40
GRADES = ["A+", "A", "B", "C", "D", "F"]


def grade(p):
    return "A+" if p >= 90 else "A" if p >= 80 else "B" if p >= 70 else "C" if p >= 60 else "D" if p >= 40 else "F"


def cluster(df):
    if len(df) < 3:
        return ["N/A"] * len(df)
    km = KMeans(n_clusters=3, n_init=10, random_state=42).fit(df[["Percentage", "Attendance"]])
    order = pd.Series(df["Percentage"].values).groupby(km.labels_).mean().sort_values().index.tolist()
    names = dict(zip(order, ["Needs Support", "Average", "High Performer"]))
    return [names[label] for label in km.labels_]


def compute(df):
    df = df.copy()
    if df.empty:
        return df
    df["Total"] = df[SUBJECTS].sum(axis=1)
    df["Percentage"] = (df["Total"] / len(SUBJECTS)).round(1)
    df["Grade"] = df["Percentage"].apply(grade)
    df["Rank"] = df["Total"].rank(ascending=False, method="min").astype(int)
    df["Result"] = np.where((df[SUBJECTS] >= PASS_MARK).all(axis=1), "Pass", "Fail")
    df["AtRisk"] = (df["Percentage"] < 50) | (df["Attendance"] < 75) | (df[SUBJECTS] < PASS_MARK).any(axis=1)
    df["Group"] = cluster(df)
    return df


def summary(df):
    corr = df["Attendance"].corr(df["Percentage"])
    return {
        "students": len(df),
        "average": round(df["Percentage"].mean(), 1),
        "pass_rate": round((df["Result"] == "Pass").mean() * 100),
        "at_risk": int(df["AtRisk"].sum()),
        "correlation": 0.0 if pd.isna(corr) else round(float(corr), 2),
    }


def subject_stats(df):
    out = []
    for s in SUBJECTS:
        out.append({"subject": s, "avg": round(df[s].mean(), 1), "high": int(df[s].max()),
                    "low": int(df[s].min()), "pass_pct": round((df[s] >= PASS_MARK).mean() * 100)})
    return out


def grade_distribution(df):
    counts = df["Grade"].value_counts()
    return [int(counts.get(g, 0)) for g in GRADES]


def fit_model(df):
    """Linear regression: attendance -> percentage. Returns (model, r2) or None."""
    if len(df) < 5:
        return None
    X, y = df[["Attendance"]].values, df["Percentage"].values
    model = LinearRegression().fit(X, y)
    return model, round(float(model.score(X, y)), 3)
