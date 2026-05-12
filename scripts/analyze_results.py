"""Statistical analysis of benchmark results."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import kruskal, shapiro

RESULTS_DIR = Path(__file__).parent.parent / "results"


def iqr_filter(series: pd.Series) -> pd.Series:
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return series[(series >= q1 - 1.5 * iqr) & (series <= q3 + 1.5 * iqr)]


def describe_method(df: pd.DataFrame, metric_col: str) -> pd.DataFrame:
    rows = []
    for method, grp in df.groupby("method"):
        values = iqr_filter(grp[metric_col].dropna())
        if len(values) < 3:
            continue
        ci_low, ci_high = stats.t.interval(
            0.95, df=len(values) - 1, loc=values.mean(), scale=stats.sem(values)
        )
        _, p_shapiro = shapiro(values[:5000])  # Shapiro limit
        rows.append(
            {
                "method": method,
                "n": len(values),
                "mean": values.mean(),
                "median": values.median(),
                "std": values.std(),
                "iqr": values.quantile(0.75) - values.quantile(0.25),
                "cv": values.std() / values.mean() if values.mean() != 0 else np.nan,
                "p50": values.quantile(0.50),
                "p75": values.quantile(0.75),
                "p90": values.quantile(0.90),
                "p95": values.quantile(0.95),
                "p99": values.quantile(0.99),
                "ci_low_95": ci_low,
                "ci_high_95": ci_high,
                "normal_p": p_shapiro,
            }
        )
    return pd.DataFrame(rows)


def significance_tests(df: pd.DataFrame, metric_col: str) -> dict:
    groups = [grp[metric_col].dropna().values for _, grp in df.groupby("method")]
    if len(groups) < 2:
        return {}
    stat, p_kruskal = kruskal(*groups)
    return {"kruskal_stat": stat, "kruskal_p": p_kruskal}


def main():
    locust_path = RESULTS_DIR / "locust_unified.csv"
    if not locust_path.exists():
        print(f"No data at {locust_path}. Run collect_results.py first.")
        return

    df = pd.read_csv(locust_path)

    metric_col = "50%"  # Locust stats median column
    if metric_col not in df.columns:
        # Fallback to first numeric col
        metric_col = df.select_dtypes(include=np.number).columns[0]

    print(f"Analysing metric: {metric_col}")
    summary = describe_method(df, metric_col)
    out_summary = RESULTS_DIR / "statistical_analysis.csv"
    summary.to_csv(out_summary, index=False)
    print(f"Saved → {out_summary}")
    print(summary.to_string(index=False))

    sig = significance_tests(df, metric_col)
    if sig:
        sig_df = pd.DataFrame([sig])
        out_sig = RESULTS_DIR / "significance_tests.csv"
        sig_df.to_csv(out_sig, index=False)
        print(f"\nKruskal-Wallis: stat={sig['kruskal_stat']:.4f}, p={sig['kruskal_p']:.6f}")
        print(f"Saved → {out_sig}")


if __name__ == "__main__":
    main()
