"""Collect and unify benchmark results from Locust CSV files and Prometheus."""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pandas as pd
import requests

RESULTS_DIR = Path(__file__).parent.parent / "results"
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")


def load_locust_stats() -> pd.DataFrame:
    # format 1 (run_all_scenarios.sh): method_uUSERS_repREP
    # format 2 (test_protocol.sh):     method_USERSu_YYYYMMDD_HHMMSS
    pat1 = re.compile(r"(?P<method>[a-z]+)_u(?P<users>\d+)_rep(?P<rep>\d+)")
    pat2 = re.compile(r"(?P<method>[a-z]+)_(?P<users>\d+)u_\d{8}_\d{6}")

    rep_counters: dict[tuple, int] = {}
    frames = []
    for path in sorted(RESULTS_DIR.glob("*_stats.csv")):
        name = path.stem.replace("_stats", "")
        m = pat1.match(name)
        if m:
            method, users, rep = m.group("method"), int(m.group("users")), int(m.group("rep"))
        else:
            m = pat2.match(name)
            if not m:
                continue
            method, users = m.group("method"), int(m.group("users"))
            key = (method, users)
            rep_counters[key] = rep_counters.get(key, 0) + 1
            rep = rep_counters[key]
        df = pd.read_csv(path)
        df["method"] = method
        df["users"] = users
        df["repetition"] = rep
        frames.append(df)
    if not frames:
        print("No Locust stats CSV files found.")
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def query_prometheus(promql: str, step: str = "15s") -> pd.DataFrame:
    end = int(time.time())
    start = end - 3600
    resp = requests.get(
        f"{PROMETHEUS_URL}/api/v1/query_range",
        params={"query": promql, "start": start, "end": end, "step": step},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json()["data"]["result"]
    rows = []
    for series in results:
        labels = series["metric"]
        for ts, val in series["values"]:
            rows.append({"timestamp": float(ts), "value": float(val), **labels})
    return pd.DataFrame(rows)


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    print("Loading Locust stats...")
    locust_df = load_locust_stats()

    print("Querying Prometheus...")
    prom_frames = []
    queries = {
        "latency_p50": 'histogram_quantile(0.50, sum(rate(request_latency_seconds_bucket[1m])) by (le, method))',
        "latency_p95": 'histogram_quantile(0.95, sum(rate(request_latency_seconds_bucket[1m])) by (le, method))',
        "latency_p99": 'histogram_quantile(0.99, sum(rate(request_latency_seconds_bucket[1m])) by (le, method))',
        "throughput": 'sum(rate(request_total[1m])) by (method)',
    }
    for metric_name, promql in queries.items():
        try:
            df = query_prometheus(promql)
            df["metric"] = metric_name
            prom_frames.append(df)
        except Exception as exc:
            print(f"  Warning: could not query {metric_name}: {exc}")

    if prom_frames:
        prom_df = pd.concat(prom_frames, ignore_index=True)
        out = RESULTS_DIR / "prometheus_metrics.csv"
        prom_df.to_csv(out, index=False)
        print(f"  Saved Prometheus metrics → {out}")

    if not locust_df.empty:
        out = RESULTS_DIR / "locust_unified.csv"
        locust_df.to_csv(out, index=False)
        print(f"  Saved unified Locust stats → {out}")

    print("Done.")


if __name__ == "__main__":
    main()
