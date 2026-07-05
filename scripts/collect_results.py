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


def prometheus_window() -> tuple[int, int]:
    """[start, end] window matched to the test run, not to "the last hour".

    Precedence: explicit PROM_START/PROM_END → modification-time span of the
    result files (with a margin) → PROM_LOOKBACK_SECONDS fallback (default 1h).
    """
    now = int(time.time())
    start_env, end_env = os.getenv("PROM_START"), os.getenv("PROM_END")
    if start_env and end_env:
        return int(start_env), int(end_env)
    files = list(RESULTS_DIR.glob("*_stats.csv"))
    if files:
        mtimes = [int(f.stat().st_mtime) for f in files]
        return min(mtimes) - 120, now
    lookback = int(os.getenv("PROM_LOOKBACK_SECONDS", "3600"))
    return now - lookback, now


def query_prometheus(promql: str, start: int, end: int, step: str = "15s") -> pd.DataFrame:
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


def container_name_map() -> dict[str, str]:
    """Map cAdvisor series ids (/docker/<hash>) to compose container names.

    cAdvisor on Docker Desktop for macOS leaves the `name` label empty, so the
    mapping has to come from the Docker CLI. Returns {} when Docker is not
    reachable (resource series are then kept with the raw id).
    """
    import subprocess

    try:
        out = subprocess.run(
            ["docker", "ps", "--no-trunc", "--format", "{{.ID}},{{.Names}}"],
            capture_output=True, text=True, timeout=10, check=True,
        ).stdout
    except Exception as exc:
        print(f"  Warning: cannot map container ids to names ({exc}).")
        return {}
    mapping = {}
    for line in out.splitlines():
        cid, _, name = line.partition(",")
        if cid and name:
            mapping[f"/docker/{cid}"] = name
    return mapping


def collect_resources(start: int, end: int) -> pd.DataFrame:
    """Container CPU (cores) and RAM (bytes) time series from cAdvisor."""
    queries = {
        "cpu_cores": 'rate(container_cpu_usage_seconds_total{id=~"/docker/.+"}[1m])',
        "ram_bytes": 'container_memory_usage_bytes{id=~"/docker/.+"}',
    }
    names = container_name_map()
    frames = []
    for metric_name, promql in queries.items():
        try:
            df = query_prometheus(promql, start, end)
        except Exception as exc:
            print(f"  Warning: could not query {metric_name}: {exc}")
            continue
        if df.empty:
            print(f"  Warning: query '{metric_name}' returned no data in the test window.")
            continue
        df["metric"] = metric_name
        df["container"] = df["id"].map(names).fillna(df["id"])
        frames.append(df[["timestamp", "value", "metric", "container"]])
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    print("Loading Locust stats...")
    locust_df = load_locust_stats()

    start, end = prometheus_window()
    print(f"Querying Prometheus (window {end - start}s, from ts={start})...")
    prom_frames = []
    queries = {
        # RPC/HTTP: server-side latency
        "latency_p50": 'histogram_quantile(0.50, sum(rate(request_latency_seconds_bucket[1m])) by (le, method))',
        "latency_p95": 'histogram_quantile(0.95, sum(rate(request_latency_seconds_bucket[1m])) by (le, method))',
        "latency_p99": 'histogram_quantile(0.99, sum(rate(request_latency_seconds_bucket[1m])) by (le, method))',
        # Messaging: end-to-end latency (producer → consumer)
        "e2e_latency_p50": 'histogram_quantile(0.50, sum(rate(e2e_latency_seconds_bucket[1m])) by (le, method))',
        "e2e_latency_p95": 'histogram_quantile(0.95, sum(rate(e2e_latency_seconds_bucket[1m])) by (le, method))',
        "e2e_latency_p99": 'histogram_quantile(0.99, sum(rate(e2e_latency_seconds_bucket[1m])) by (le, method))',
        "throughput": 'sum(rate(request_total[1m])) by (method)',
    }
    for metric_name, promql in queries.items():
        try:
            df = query_prometheus(promql, start, end)
            if df.empty:
                print(f"  Warning: query '{metric_name}' returned no data in the test window.")
                continue
            df["metric"] = metric_name
            prom_frames.append(df)
        except Exception as exc:
            print(f"  Warning: could not query {metric_name}: {exc}")

    if prom_frames:
        prom_df = pd.concat(prom_frames, ignore_index=True)
        out = RESULTS_DIR / "prometheus_metrics.csv"
        prom_df.to_csv(out, index=False)
        print(f"  Saved Prometheus metrics → {out}")
    else:
        print("  No Prometheus data — check the time window and whether services were scraped.")

    print("Collecting container resources (cAdvisor)...")
    res_df = collect_resources(start, end)
    if not res_df.empty:
        out = RESULTS_DIR / "container_resources.csv"
        res_df.to_csv(out, index=False)
        print(f"  Saved container resources → {out}")

    if not locust_df.empty:
        out = RESULTS_DIR / "locust_unified.csv"
        locust_df.to_csv(out, index=False)
        print(f"  Saved unified Locust stats → {out}")

    print("Done.")


if __name__ == "__main__":
    main()
