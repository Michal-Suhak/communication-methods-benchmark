"""Generate comparison charts from benchmark results."""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

RESULTS_DIR = Path(__file__).parent.parent / "results"
CHARTS_DIR = RESULTS_DIR / "charts"

METHOD_COLORS = {
    "rest": "#2196F3",
    "grpc": "#4CAF50",
    "graphql": "#E91E63",
    "amqp": "#FF9800",
    "kafka": "#9C27B0",
}

plt.rcParams.update({"figure.dpi": 300, "font.size": 10})


def _save(fig: plt.Figure, name: str):
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "svg"):
        path = CHARTS_DIR / f"{name}.{ext}"
        fig.savefig(path, bbox_inches="tight")
        print(f"  Saved {path}")
    plt.close(fig)


def bar_latency(df: pd.DataFrame):
    percentiles = ["p50", "p95", "p99"]
    missing = [p for p in percentiles if p not in df.columns]
    if missing:
        print(f"  Skipping bar_latency: missing columns {missing}")
        return
    methods = df["method"].tolist()
    x = np.arange(len(methods))
    width = 0.25
    # Colour encodes the percentile (consistent with the legend); X axis groups methods.
    pct_colors = {"p50": "#90CAF9", "p95": "#1976D2", "p99": "#0D47A1"}
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, pct in enumerate(percentiles):
        ax.bar(x + i * width, df[pct], width, label=pct, color=pct_colors[pct])
    ax.set_xticks(x + width)
    ax.set_xticklabels(methods)
    ax.set_ylabel("Opóźnienie (ms)")
    ax.set_title("Percentyle opóźnienia p50 / p95 / p99 wg metody")
    ax.legend(title="percentyl")
    _save(fig, "latency_bar")


def box_latency(raw_df: pd.DataFrame, metric_col: str):
    fig, ax = plt.subplots(figsize=(10, 5))
    methods = sorted(raw_df["method"].unique())
    data = [raw_df[raw_df["method"] == m][metric_col].dropna().values for m in methods]
    bp = ax.boxplot(data, tick_labels=methods, patch_artist=True)
    for patch, method in zip(bp["boxes"], methods):
        patch.set_facecolor(METHOD_COLORS.get(method, "#999"))
    ax.set_ylabel(f"Opóźnienie (ms) — {metric_col}")
    ax.set_title("Rozkład opóźnienia wg metody")
    _save(fig, "latency_boxplot")


def heatmap(df: pd.DataFrame):
    numeric_cols = ["mean", "p50", "p95", "p99", "std"]
    available = [c for c in numeric_cols if c in df.columns]
    if not available:
        return
    matrix = df.set_index("method")[available]
    normalized = (matrix - matrix.min()) / (matrix.max() - matrix.min() + 1e-12)
    fig, ax = plt.subplots(figsize=(8, 4))
    sns.heatmap(normalized, annot=matrix.round(4), fmt="g", cmap="RdYlGn_r", ax=ax, cbar=True)
    ax.set_title("Macierz porównawcza (znormalizowana; niżej = lepiej)")
    _save(fig, "heatmap")


def radar(df: pd.DataFrame):
    metrics = ["mean", "p95", "std"]
    available = [m for m in metrics if m in df.columns]
    if len(available) < 2:
        return
    methods = df["method"].tolist()
    N = len(available)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"polar": True})
    for _, row in df.iterrows():
        vals = [row[m] for m in available]
        max_vals = df[available].max()
        norm = [v / (max_val + 1e-12) for v, max_val in zip(vals, max_vals)]
        norm += norm[:1]
        ax.plot(angles, norm, label=row["method"], color=METHOD_COLORS.get(row["method"], "#999"))
        ax.fill(angles, norm, alpha=0.1, color=METHOD_COLORS.get(row["method"], "#999"))
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(available)
    ax.set_title("Porównanie wielowymiarowe")
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    _save(fig, "radar")


def _line_vs_users(by_level: pd.DataFrame, value_col: str, ylabel: str, title: str, name: str):
    if value_col not in by_level.columns:
        print(f"  Skipping {name}: missing column {value_col}")
        return
    fig, ax = plt.subplots(figsize=(10, 5))
    for method, grp in by_level.groupby("method"):
        grp = grp.sort_values("users")
        ax.plot(grp["users"], grp[value_col], marker="o",
                label=method, color=METHOD_COLORS.get(method, "#999"))
    ax.set_xscale("log")
    ax.set_xticks(sorted(by_level["users"].unique()))
    ax.get_xaxis().set_major_formatter(plt.ScalarFormatter())
    ax.set_xlabel("Liczba równoczesnych użytkowników")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend(title="metoda")
    _save(fig, name)


_PAYLOAD_RE = re.compile(r"(?:size_kb=|\[(?:full,)?)(\d+)\s*(?:kb)?\]?", re.IGNORECASE)


def latency_vs_payload(raw: pd.DataFrame):
    """Median latency for the large scenario per payload size (lowest load level).

    GraphQL 'partial' endpoints are excluded — a field-subset response is not the
    same payload as the full one.
    """
    df = raw[raw["Name"] != "Aggregated"].copy()
    df = df[~df["Name"].str.contains("partial", case=False, na=False)]
    df["payload_kb"] = df["Name"].apply(
        lambda n: int(m.group(1)) if (m := _PAYLOAD_RE.search(str(n))) else None
    )
    df = df.dropna(subset=["payload_kb"])
    if df.empty or "users" not in df.columns:
        print("  Skipping latency_vs_payload: no per-size endpoints found.")
        return
    base_level = df["users"].min()
    df = df[df["users"] == base_level]
    pivot = df.groupby(["method", "payload_kb"])["50%"].mean().unstack()

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(pivot.index))
    width = 0.8 / max(len(pivot.columns), 1)
    for i, size_kb in enumerate(sorted(pivot.columns)):
        ax.bar(x + i * width, pivot[size_kb], width, label=f"{int(size_kb)} KB")
    ax.set_xticks(x + width * (len(pivot.columns) - 1) / 2)
    ax.set_xticklabels(pivot.index)
    ax.set_ylabel("Mediana opóźnienia (ms)")
    ax.set_title(f"Opóźnienie a rozmiar ładunku — scenariusz large, {int(base_level)} użytkowników")
    ax.legend(title="ładunek")
    _save(fig, "latency_vs_payload")


def timeline(history_glob: str, title: str, name: str):
    """Median latency and failure rate over test time, from *_stats_history.csv."""
    frames = []
    pat = re.compile(r"(?P<method>[a-z]+)_u\d+_rep1_stats_history")
    for path in sorted(RESULTS_DIR.glob(history_glob)):
        m = pat.match(path.stem)
        if not m:
            continue
        h = pd.read_csv(path)
        if h.empty or "Timestamp" not in h.columns:
            continue
        h["method"] = m.group("method")
        h["t"] = h["Timestamp"] - h["Timestamp"].min()
        frames.append(h)
    if not frames:
        print(f"  Skipping {name}: no history files match {history_glob}")
        return
    df = pd.concat(frames, ignore_index=True)

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    for method, grp in df.groupby("method"):
        color = METHOD_COLORS.get(method, "#999")
        ax1.plot(grp["t"], grp["Total Median Response Time"], label=method, color=color)
        if "Failures/s" in grp:
            ax2.plot(grp["t"], grp["Failures/s"], label=method, color=color)
    ax1.set_ylabel("Mediana opóźnienia (ms)")
    ax1.set_title(title)
    ax1.legend(title="metoda")
    ax2.set_ylabel("Błędy/s")
    ax2.set_xlabel("Czas testu (s)")
    _save(fig, name)


def resources_chart():
    """Peak CPU (cores) and RAM (MiB) per container, from container_resources.csv."""
    path = RESULTS_DIR / "container_resources.csv"
    if not path.exists():
        print("  Skipping resources chart: no container_resources.csv")
        return
    df = pd.read_csv(path)
    if df.empty:
        return
    df["container"] = (
        df["container"]
        .str.replace("communication-methods-benchmark-", "", regex=False)
        .str.replace(r"-\d+$", "", regex=True)
    )
    keep = ["rest-server", "grpc-server", "graphql-server", "amqp-consumer",
            "kafka-consumer", "rabbitmq", "kafka", "zookeeper", "locust"]
    df = df[df["container"].isin(keep)]
    if df.empty:
        print("  Skipping resources chart: no benchmark containers in data.")
        return
    peak = df.groupby(["container", "metric"])["value"].max().unstack()

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
    order = [c for c in keep if c in peak.index]
    if "cpu_cores" in peak:
        ax1.barh(order, [peak.loc[c, "cpu_cores"] for c in order], color="#1976D2")
        ax1.set_xlabel("Szczytowe CPU (rdzenie)")
    if "ram_bytes" in peak:
        ax2.barh(order, [peak.loc[c, "ram_bytes"] / 2**20 for c in order], color="#E64A19")
        ax2.set_xlabel("Szczytowa pamięć RAM (MiB)")
    fig.suptitle("Zużycie zasobów kontenerów (szczyt w oknie testu)")
    _save(fig, "resources")


def main():
    stats_path = RESULTS_DIR / "statistical_analysis.csv"
    by_level_path = RESULTS_DIR / "statistical_analysis_by_level.csv"
    locust_path = RESULTS_DIR / "locust_unified.csv"

    if not stats_path.exists():
        print(f"Run analyze_results.py first (missing {stats_path})")
        return

    # The file may be empty when analyze_results.py skipped every group
    # (fewer than 3 repetitions per method) — skip the aggregate charts then,
    # the box plot from raw data still makes sense.
    try:
        df = pd.read_csv(stats_path)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame()

    if df.empty:
        print(f"No aggregate statistics in {stats_path} (not enough repetitions?) — "
              "skipping bar chart / heatmap / radar.")
    else:
        print("Generating bar chart...")
        bar_latency(df)

        print("Generating heatmap...")
        heatmap(df)

        print("Generating radar chart...")
        radar(df)

    if by_level_path.exists():
        try:
            by_level = pd.read_csv(by_level_path)
        except pd.errors.EmptyDataError:
            by_level = pd.DataFrame()
        if not by_level.empty:
            print("Generating per-level line charts...")
            _line_vs_users(by_level, "throughput_rps", "Przepustowość (req/s)",
                           "Przepustowość a liczba użytkowników", "throughput_vs_users")
            _line_vs_users(by_level, "p50", "Mediana opóźnienia (ms)",
                           "Mediana opóźnienia a liczba użytkowników", "latency_vs_users")

    if locust_path.exists():
        raw_all = pd.read_csv(locust_path)
        print("Generating latency vs payload chart...")
        latency_vs_payload(raw_all)

        # Aggregate rows only — consistent with analyze_results.py.
        raw = raw_all
        if "Name" in raw.columns and (raw["Name"] == "Aggregated").any():
            raw = raw[raw["Name"] == "Aggregated"]
        metric_col = "50%" if "50%" in raw.columns else raw.select_dtypes("number").columns[0]
        print("Generating box plot...")
        box_latency(raw, metric_col)

    print("Generating timelines...")
    timeline("*_u2000_rep1_stats_history.csv", "Obciążenie szczytowe (2000 użytkowników)", "spike_timeline")
    timeline("*_u50_rep1_stats_history.csv", "Test długotrwały (50 użytkowników)", "longrun_timeline")

    print("Generating resources chart...")
    resources_chart()

    print("Done.")


if __name__ == "__main__":
    main()
