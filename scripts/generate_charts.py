"""Generate comparison charts from benchmark results."""
from __future__ import annotations

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
    # Kodowanie: kolor = percentyl (spójne z legendą). Oś X grupuje metody.
    pct_colors = {"p50": "#90CAF9", "p95": "#1976D2", "p99": "#0D47A1"}
    fig, ax = plt.subplots(figsize=(10, 5))
    for i, pct in enumerate(percentiles):
        ax.bar(x + i * width, df[pct], width, label=pct, color=pct_colors[pct])
    ax.set_xticks(x + width)
    ax.set_xticklabels(methods)
    ax.set_ylabel("Latency (ms)")
    ax.set_title("Latency p50 / p95 / p99 per method")
    ax.legend(title="percentyl")
    _save(fig, "latency_bar")


def box_latency(raw_df: pd.DataFrame, metric_col: str):
    fig, ax = plt.subplots(figsize=(10, 5))
    methods = sorted(raw_df["method"].unique())
    data = [raw_df[raw_df["method"] == m][metric_col].dropna().values for m in methods]
    bp = ax.boxplot(data, tick_labels=methods, patch_artist=True)
    for patch, method in zip(bp["boxes"], methods):
        patch.set_facecolor(METHOD_COLORS.get(method, "#999"))
    ax.set_ylabel(f"Latency (ms) — {metric_col}")
    ax.set_title("Latency distribution per method")
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
    ax.set_title("Performance heatmap (normalised; lower = better)")
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
    ax.set_title("Radar comparison")
    ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1))
    _save(fig, "radar")


def main():
    stats_path = RESULTS_DIR / "statistical_analysis.csv"
    locust_path = RESULTS_DIR / "locust_unified.csv"

    if not stats_path.exists():
        print(f"Run analyze_results.py first (missing {stats_path})")
        return

    # Plik bywa pusty, gdy analyze_results.py pominął wszystkie grupy (n<3 powtórzeń
    # na metodę) — wtedy pomijamy wykresy zagregowane, ale box plot z surowych danych
    # nadal ma sens.
    try:
        df = pd.read_csv(stats_path)
    except pd.errors.EmptyDataError:
        df = pd.DataFrame()

    if df.empty:
        print(f"Brak zagregowanych statystyk w {stats_path} (za mało powtórzeń?) — "
              "pomijam bar chart / heatmap / radar.")
    else:
        print("Generating bar chart...")
        bar_latency(df)

        print("Generating heatmap...")
        heatmap(df)

        print("Generating radar chart...")
        radar(df)

    if locust_path.exists():
        raw = pd.read_csv(locust_path)
        # Tylko wiersze zbiorcze — spójnie z analyze_results.py (bez mieszania endpointów).
        if "Name" in raw.columns and (raw["Name"] == "Aggregated").any():
            raw = raw[raw["Name"] == "Aggregated"]
        metric_col = "50%" if "50%" in raw.columns else raw.select_dtypes("number").columns[0]
        print("Generating box plot...")
        box_latency(raw, metric_col)

    print("Done.")


if __name__ == "__main__":
    main()
