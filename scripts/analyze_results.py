"""Statistical analysis of benchmark results.

Jednostka latencji: milisekundy (kolumny Locusta). Populacja analizy to wyłącznie
wiersze `Aggregated` Locusta — jeden wynik na (metoda, poziom obciążenia, powtórzenie).
Percentyle p50/p95/p99 to ŚREDNIA odpowiedniego percentyla po powtórzeniach,
a NIE percentyl liczony z już zagregowanych percentyli.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import kruskal, shapiro

RESULTS_DIR = Path(__file__).parent.parent / "results"

# Kolumny percentyli w Locust *_stats.csv (już zagregowane po surowych próbkach).
PCT_COLS = {"p50": "50%", "p95": "95%", "p99": "99%"}
METRIC_COL = "50%"  # mediana latencji na powtórzenie (ms)


def iqr_filter(series: pd.Series) -> pd.Series:
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    return series[(series >= q1 - 1.5 * iqr) & (series <= q3 + 1.5 * iqr)]


def select_population(df: pd.DataFrame) -> pd.DataFrame:
    """Zostaw tylko wiersze zbiorcze Locusta (Name == 'Aggregated').

    Bez tego analiza miesza wiersze per-endpoint (echo, small, large 50/100 KB)
    z wierszem zbiorczym, traktując różne payloady jak powtórzenia tej samej wielkości.
    """
    if "Name" in df.columns:
        agg = df[df["Name"] == "Aggregated"]
        if not agg.empty:
            return agg
        print("  Uwaga: brak wierszy 'Aggregated' — używam wszystkich wierszy.")
    else:
        print("  Uwaga: brak kolumny 'Name' — używam wszystkich wierszy.")
    return df


def describe_method(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for method, grp in df.groupby("method"):
        values = iqr_filter(grp[METRIC_COL].dropna())
        if len(values) < 3:
            print(f"  Pomijam {method}: za mało próbek (n={len(values)}).")
            continue
        mean, std = values.mean(), values.std()
        sem = stats.sem(values)
        if np.isfinite(sem) and sem > 0:
            ci_low, ci_high = stats.t.interval(0.95, df=len(values) - 1, loc=mean, scale=sem)
        else:
            ci_low = ci_high = mean  # zerowa wariancja / pojedyncza wartość
        normal_p = shapiro(values)[1] if len(values) >= 8 else np.nan
        row = {
            "method": method,
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
        # Percentyle = średnia tego samego percentyla po powtórzeniach (poprawne).
        for out_col, src_col in PCT_COLS.items():
            row[out_col] = grp[src_col].dropna().mean() if src_col in grp else np.nan
        rows.append(row)
    return pd.DataFrame(rows)


def significance_tests(df: pd.DataFrame):
    """Zwraca (wynik_omnibus: dict, posthoc: DataFrame|None).

    Wybór testu zależy od normalności: jeśli wszystkie grupy są normalne (Shapiro,
    n>=8) → ANOVA + Tukey HSD; w przeciwnym razie Kruskal-Wallis + Dunn (Bonferroni).
    """
    groups = {m: g[METRIC_COL].dropna().values for m, g in df.groupby("method")}
    groups = {m: v for m, v in groups.items() if len(v) > 0}
    if len(groups) < 2:
        return {}, None

    all_normal = all(len(v) >= 8 and shapiro(v)[1] > 0.05 for v in groups.values())
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
            print(f"  Tukey HSD pominięty: {exc}")
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
            print(f"  Test Dunna pominięty (brak scikit-posthocs?): {exc}")

    return result, posthoc


def main():
    locust_path = RESULTS_DIR / "locust_unified.csv"
    if not locust_path.exists():
        print(f"No data at {locust_path}. Run collect_results.py first.")
        return

    df = pd.read_csv(locust_path)
    if METRIC_COL not in df.columns:
        print(f"Brak kolumny '{METRIC_COL}' w {locust_path} — nie mogę analizować latencji.")
        return

    df = select_population(df)
    print(f"Analizuję latencję (ms) na podstawie {len(df)} wierszy zbiorczych.")

    summary = describe_method(df)
    out_summary = RESULTS_DIR / "statistical_analysis.csv"
    summary.to_csv(out_summary, index=False)
    print(f"Saved → {out_summary}")
    if not summary.empty:
        print(summary.to_string(index=False))

    result, posthoc = significance_tests(df)
    if result:
        pd.DataFrame([result]).to_csv(RESULTS_DIR / "significance_tests.csv", index=False)
        print(f"\nOmnibus ({result['test']}): stat={result['stat']:.4f}, p={result['p']:.6f}")
        if posthoc is not None:
            name = "posthoc_tukey.csv" if result["test"] == "anova" else "posthoc_dunn.csv"
            posthoc.to_csv(RESULTS_DIR / name)
            print(f"Saved post-hoc → {RESULTS_DIR / name}")


if __name__ == "__main__":
    main()
