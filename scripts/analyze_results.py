"""Statistical analysis of benchmark results.

Latency unit: milliseconds (Locust columns). The analysed population consists
exclusively of Locust `Aggregated` rows — one result per (method, load level,
repetition). The p50/p95/p99 columns are the MEAN of the same percentile across
repetitions, never a percentile computed from already-aggregated percentiles.

Outputs:
  statistical_analysis.csv           per-method stats, all load levels pooled
  statistical_analysis_by_level.csv  per (method, users) stats — thesis tables
  significance_tests.csv             omnibus test on the pooled population
  significance_by_level.csv          omnibus test per load level
  posthoc_{dunn,tukey}.csv           pairwise post-hoc, pooled population
  posthoc_{dunn,tukey}_u{N}.csv      pairwise post-hoc per load level
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import kruskal, shapiro

RESULTS_DIR = Path(__file__).parent.parent / "results"

# Percentile columns in Locust *_stats.csv (already aggregated over raw samples).
PCT_COLS = {"p50": "50%", "p95": "95%", "p99": "99%"}
METRIC_COL = "50%"  # median latency per repetition (ms)
# Below this group size the Shapiro-Wilk test has no power — report NaN instead.
SHAPIRO_MIN_N = 20


def iqr_filter(series: pd.Series) -> pd.Series:
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return series[(series >= q1 - 1.5 * iqr) & (series <= q3 + 1.5 * iqr)]


def select_population(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only Locust aggregate rows (Name == 'Aggregated').

    Without this filter the analysis would mix per-endpoint rows (echo, small,
    large 50/100 KB) with the aggregate row, treating different payloads as
    repetitions of the same quantity.
    """
    if "Name" in df.columns:
        agg = df[df["Name"] == "Aggregated"]
        if not agg.empty:
            return agg
        print("  Warning: no 'Aggregated' rows — using all rows.")
    else:
        print("  Warning: no 'Name' column — using all rows.")
    return df


def describe(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows = []
    for key, grp in df.groupby(group_cols):
        key = key if isinstance(key, tuple) else (key,)
        values = iqr_filter(grp[METRIC_COL].dropna())
        if len(values) < 3:
            print(f"  Skipping {key}: not enough samples (n={len(values)}).")
            continue
        mean, std = values.mean(), values.std()
        sem = stats.sem(values)
        if np.isfinite(sem) and sem > 0:
            ci_low, ci_high = stats.t.interval(0.95, df=len(values) - 1, loc=mean, scale=sem)
        else:
            ci_low = ci_high = mean  # zero variance / single value
        normal_p = shapiro(values)[1] if len(values) >= SHAPIRO_MIN_N else np.nan
        row = dict(zip(group_cols, key))
        row.update(
            {
                "n": len(values),
                "mean": mean,
                "median": values.median(),
                "std": std,
                "iqr": values.quantile(0.75) - values.quantile(0.25),
                "cv": std / mean if mean else np.nan,
                "ci_low_95": ci_low,
                "ci_high_95": ci_high,
                "normal_p": normal_p,
            }
        )
        # Percentiles = mean of the same percentile across repetitions.
        for out_col, src_col in PCT_COLS.items():
            row[out_col] = grp[src_col].dropna().mean() if src_col in grp else np.nan
        if "Requests/s" in grp:
            row["throughput_rps"] = grp["Requests/s"].dropna().mean()
        if {"Failure Count", "Request Count"} <= set(grp.columns):
            total = grp["Request Count"].sum()
            row["fail_pct"] = 100 * grp["Failure Count"].sum() / total if total else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def significance_tests(df: pd.DataFrame):
    """Return (omnibus result: dict, posthoc: DataFrame|None).

    Test selection depends on normality: if every group is normal (Shapiro,
    n>=SHAPIRO_MIN_N) → ANOVA + Tukey HSD; otherwise Kruskal-Wallis + Dunn
    (Bonferroni).
    """
    groups = {m: g[METRIC_COL].dropna().values for m, g in df.groupby("method")}
    groups = {m: v for m, v in groups.items() if len(v) > 0}
    if len(groups) < 2:
        return {}, None

    all_normal = all(
        len(v) >= SHAPIRO_MIN_N and shapiro(v)[1] > 0.05 for v in groups.values()
    )
    long = df[["method", METRIC_COL]].dropna()

    if all_normal:
        stat, p = stats.f_oneway(*groups.values())
        result = {"test": "anova", "stat": stat, "p": p}
        posthoc = None
        try:
            from statsmodels.stats.multicomp import pairwise_tukeyhsd

            tuk = pairwise_tukeyhsd(long[METRIC_COL], long["method"])
            posthoc = pd.DataFrame(tuk._results_table.data[1:], columns=tuk._results_table.data[0])
        except Exception as exc:
            print(f"  Tukey HSD skipped: {exc}")
    else:
        stat, p = kruskal(*groups.values())
        result = {"test": "kruskal", "stat": stat, "p": p}
        posthoc = None
        try:
            import scikit_posthocs as sp

            posthoc = sp.posthoc_dunn(
                long, val_col=METRIC_COL, group_col="method", p_adjust="bonferroni"
            )
        except Exception as exc:
            print(f"  Dunn test skipped (scikit-posthocs missing?): {exc}")

    return result, posthoc


def _save_posthoc(posthoc: pd.DataFrame | None, test: str, suffix: str = ""):
    if posthoc is None:
        return
    name = f"posthoc_{'tukey' if test == 'anova' else 'dunn'}{suffix}.csv"
    posthoc.to_csv(RESULTS_DIR / name)
    print(f"Saved post-hoc → {RESULTS_DIR / name}")


def main():
    locust_path = RESULTS_DIR / "locust_unified.csv"
    if not locust_path.exists():
        print(f"No data at {locust_path}. Run collect_results.py first.")
        return

    df = pd.read_csv(locust_path)
    if METRIC_COL not in df.columns:
        print(f"Column '{METRIC_COL}' missing in {locust_path} — cannot analyse latency.")
        return

    df = select_population(df)
    print(f"Analysing latency (ms) over {len(df)} aggregate rows.")

    # Pooled population (all load levels together) — kept for backward compatibility.
    summary = describe(df, ["method"])
    out_summary = RESULTS_DIR / "statistical_analysis.csv"
    summary.to_csv(out_summary, index=False)
    print(f"Saved → {out_summary}")
    if not summary.empty:
        print(summary.to_string(index=False))

    result, posthoc = significance_tests(df)
    if result:
        pd.DataFrame([result]).to_csv(RESULTS_DIR / "significance_tests.csv", index=False)
        print(f"\nOmnibus ({result['test']}): stat={result['stat']:.4f}, p={result['p']:.6f}")
        _save_posthoc(posthoc, result["test"])

    # Per load level — the population used for the thesis result tables.
    if "users" not in df.columns:
        print("Column 'users' missing — skipping per-level analysis.")
        return

    by_level = describe(df, ["method", "users"])
    out_level = RESULTS_DIR / "statistical_analysis_by_level.csv"
    by_level.to_csv(out_level, index=False)
    print(f"\nSaved → {out_level}")

    level_results = []
    for users, level_df in df.groupby("users"):
        result, posthoc = significance_tests(level_df)
        if not result:
            continue
        result["users"] = users
        level_results.append(result)
        print(f"Omnibus u{users} ({result['test']}): stat={result['stat']:.4f}, p={result['p']:.6f}")
        _save_posthoc(posthoc, result["test"], suffix=f"_u{users}")
    if level_results:
        pd.DataFrame(level_results).to_csv(RESULTS_DIR / "significance_by_level.csv", index=False)
        print(f"Saved → {RESULTS_DIR / 'significance_by_level.csv'}")


if __name__ == "__main__":
    main()
