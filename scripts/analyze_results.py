"""Statistical analysis of benchmark results.

Latency unit: milliseconds (Locust columns). The analysed population consists
exclusively of Locust `Aggregated` rows — one result per (method, load level,
repetition). The p50/p95/p99 columns are the MEAN of the same percentile across
repetitions, never a percentile computed from already-aggregated percentiles.

The scaling analysis (sweep + per-level significance + scaling charts) uses the
throughput scenario ONLY. The spike (2000) and long_running (50) levels are
separate scenarios with their own tables/timeline charts and are never plotted
as points on the throughput scaling curve nor tested as load levels.

Outputs:
  statistical_analysis.csv           per-method stats, throughput levels pooled
  statistical_analysis_by_level.csv  per (method, users) throughput stats — scaling
  statistical_analysis_scenarios.csv per (scenario, method, users) — spike/long
  significance_tests.csv             omnibus test on the pooled throughput population
  significance_by_level.csv          omnibus test per throughput load level
  posthoc_{dunn,tukey}.csv           pairwise post-hoc, pooled throughput population
  posthoc_{dunn,tukey}_u{N}.csv      pairwise post-hoc per throughput load level
  resource_usage_by_window.csv       CPU/RAM per method, active window of that method
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

# Load levels belong to distinct scenarios. Only the throughput scenario forms
# the steady-state load sweep (10/100/500/1000, 60 s, 5 reps). The spike (2000,
# ramp) and long_running (50, 300 s) levels are separate scenarios and must NOT
# be plotted as points on the throughput scaling curve nor tested as load levels.
SPIKE_USERS = 2000
LONG_RUNNING_USERS = 50


# cAdvisor samples the whole campaign, in which each protocol is exercised for
# only ~1/5 of the window. Averaging a broker over the full window mixes its
# active load with the idle stretches during other protocols' runs, which is not
# comparable with a server averaged the same way. Every component is therefore
# aggregated over the active window of ITS OWN protocol, delimited by the
# container that is busy only while that protocol runs.
WINDOW_OWNER = {
    "rest": "rest-server",
    "grpc": "grpc-server",
    "graphql": "graphql-server",
    "amqp": "amqp-consumer",
}
# Component whose usage is reported per method (broker for the async methods).
RESOURCE_COMPONENT = {
    "rest": "rest-server",
    "grpc": "grpc-server",
    "graphql": "graphql-server",
    "amqp": "rabbitmq",
    "kafka": "kafka",
}
CONSUMER_COMPONENT = {"amqp": "amqp-consumer", "kafka": "kafka-consumer"}
# Fraction of a container's peak CPU above which it counts as actively loaded.
ACTIVE_CPU_FRACTION = 0.15


def scenario_of(users: int) -> str:
    if users == SPIKE_USERS:
        return "spike"
    if users == LONG_RUNNING_USERS:
        return "long_running"
    return "throughput"


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
        raw_values = grp[METRIC_COL].dropna()
        values = iqr_filter(raw_values)
        dropped = len(raw_values) - len(values)
        if dropped:
            print(f"  IQR: dropped {dropped}/{len(raw_values)} samples in {key}.")
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


def _active_windows(cpu: pd.DataFrame) -> dict[str, tuple[float, float]]:
    """Active (start, end) timestamp per method, from its owner container's CPU."""
    windows = {}
    for method, owner in WINDOW_OWNER.items():
        series = cpu[cpu["component"] == owner]
        if series.empty:
            continue
        busy = series[series["value"] > series["value"].max() * ACTIVE_CPU_FRACTION]
        windows[method] = (busy["timestamp"].min(), busy["timestamp"].max())
    # The Kafka consumer polls the broker for the whole campaign, so it cannot
    # delimit a window. Kafka's slot is the longest stretch left over once the
    # other four protocols' windows are removed.
    stamps = sorted(cpu[cpu["component"] == "kafka"]["timestamp"].unique())
    free = [t for t in stamps if not any(lo <= t <= hi for lo, hi in windows.values())]
    if free:
        blocks, current = [], [free[0]]
        for t in free[1:]:
            if t - current[-1] <= 60:
                current.append(t)
            else:
                blocks.append(current)
                current = [t]
        blocks.append(current)
        longest = max(blocks, key=len)
        windows["kafka"] = (longest[0], longest[-1])
    # A window that collapses to nothing or swallows the campaign means the
    # detection heuristic missed — the resulting averages would be meaningless.
    campaign = stamps[-1] - stamps[0]
    for method, (lo, hi) in windows.items():
        share = (hi - lo) / campaign
        if not 0.05 < share < 0.6:
            print(f"  WARNING: {method} active window is {share:.0%} of the campaign — check detection.")
    return windows


def resource_usage_by_window() -> pd.DataFrame:
    """CPU/RAM per method, each averaged over that method's own active window."""
    path = RESULTS_DIR / "container_resources.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    df["component"] = (
        df["container"].str.replace("communication-methods-benchmark-", "", regex=False).str.replace(r"-1$", "", regex=True)
    )
    cpu = df[df["metric"] == "cpu_cores"]
    ram = df[df["metric"] == "ram_bytes"]
    windows = _active_windows(cpu)

    rows = []
    for method, (lo, hi) in windows.items():
        for role, component in (
            ("server", RESOURCE_COMPONENT[method]),
            ("consumer", CONSUMER_COMPONENT.get(method)),
        ):
            if component is None:
                continue
            c = cpu[(cpu["component"] == component) & cpu["timestamp"].between(lo, hi)]["value"]
            r = ram[(ram["component"] == component) & ram["timestamp"].between(lo, hi)]["value"]
            if c.empty:
                continue
            rows.append({
                "method": method,
                "role": role,
                "component": component,
                "window_minutes": round((hi - lo) / 60, 1),
                "cpu_mean_pct": round(100 * c.mean(), 1),
                "cpu_max_pct": round(100 * c.max(), 1),
                "ram_mean_mib": round(r.mean() / 2**20, 1) if not r.empty else float("nan"),
                "ram_max_mib": round(r.max() / 2**20, 1) if not r.empty else float("nan"),
            })
    return pd.DataFrame(rows)


def significance_tests(df: pd.DataFrame):
    """Return (omnibus result: dict, posthoc: DataFrame|None).

    Test selection depends on normality: if every group is normal (Shapiro,
    n>=SHAPIRO_MIN_N) → ANOVA + Tukey HSD; otherwise Kruskal-Wallis + Dunn
    (Bonferroni).
    """
    groups = {m: g[METRIC_COL].dropna().values for m, g in df.groupby("method")}
    # Below 3 observations per group an omnibus test has no power
    # (e.g. long_running with a single repetition).
    groups = {m: v for m, v in groups.items() if len(v) >= 3}
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

    # Split scenarios: the load sweep (scaling charts, per-level significance)
    # must use the throughput scenario ONLY. Spike/long_running keep their own
    # dedicated tables and timeline charts, never mixed into the sweep.
    if "users" in df.columns:
        df["scenario"] = df["users"].map(scenario_of)
        thr = df[df["scenario"] == "throughput"]
        other = df[df["scenario"] != "throughput"]
    else:
        thr, other = df, df.iloc[0:0]
    print(f"Analysing latency (ms): {len(thr)} throughput rows, {len(other)} spike/long-running rows.")

    # Pooled throughput population (all throughput load levels together).
    summary = describe(thr, ["method"])
    out_summary = RESULTS_DIR / "statistical_analysis.csv"
    summary.to_csv(out_summary, index=False)
    print(f"Saved → {out_summary}")
    if not summary.empty:
        print(summary.to_string(index=False))

    result, posthoc = significance_tests(thr)
    if result:
        pd.DataFrame([result]).to_csv(RESULTS_DIR / "significance_tests.csv", index=False)
        print(f"\nOmnibus ({result['test']}): stat={result['stat']:.4f}, p={result['p']:.6f}")
        _save_posthoc(posthoc, result["test"])

    if "users" not in df.columns:
        print("Column 'users' missing — skipping per-level analysis.")
        return

    # Per load level — the throughput scaling sweep (feeds the scaling charts).
    by_level = describe(thr, ["method", "users"])
    out_level = RESULTS_DIR / "statistical_analysis_by_level.csv"
    by_level.to_csv(out_level, index=False)
    print(f"\nSaved → {out_level}")

    # Spike + long_running per (scenario, method, level) — kept separately for
    # the dedicated scenario tables (traceability), never mixed into the sweep.
    if not other.empty:
        scen = describe(other, ["scenario", "method", "users"])
        scen.to_csv(RESULTS_DIR / "statistical_analysis_scenarios.csv", index=False)
        print(f"Saved → {RESULTS_DIR / 'statistical_analysis_scenarios.csv'}")

    level_results = []
    for users, level_df in thr.groupby("users"):
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

    resources = resource_usage_by_window()
    if not resources.empty:
        out_res = RESULTS_DIR / "resource_usage_by_window.csv"
        resources.to_csv(out_res, index=False)
        print(f"Saved → {out_res}")
        print(resources.to_string(index=False))


if __name__ == "__main__":
    main()
