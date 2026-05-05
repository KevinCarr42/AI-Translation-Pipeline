import json

import numpy as np
import pandas as pd

from scitrans import config

RATIO_COLUMNS = ["len_ratio", "verb_ratio", "noun_ratio", "entity_ratio", "clause_ratio"]
N_STDEV = 2.0


def calculate_thresholds(dataframe, ratio_columns=RATIO_COLUMNS, n_stdev=N_STDEV):
    # Ratios are log-symmetric (0.5 and 2.0 are equally extreme), so we compute the +/- n*stdev
    # band in log-space and exponentiate. This avoids negative lower bounds and gives
    # interpretable, ratio-symmetric cutoffs.
    thresholds = {}
    for column in ratio_columns:
        series = dataframe[column].astype(float)
        series = series[series.notna() & (series > 0) & np.isfinite(series)]
        log_series = np.log(series)
        log_mean = float(log_series.mean())
        log_std = float(log_series.std())
        lower = float(np.exp(log_mean - n_stdev * log_std))
        upper = float(np.exp(log_mean + n_stdev * log_std))
        thresholds[column] = {
            "lower": round(lower, 4),
            "upper": round(upper, 4),
            "mean": round(float(series.mean()), 4),
            "std": round(float(series.std()), 4),
            "log_mean": round(log_mean, 4),
            "log_std": round(log_std, 4),
            "n_rows": int(series.shape[0]),
        }
    return thresholds


def main():
    print(f"loading {config.WORDDOC_MATCHED_DATA_WITH_FEATURES}")
    df = pd.read_pickle(config.WORDDOC_MATCHED_DATA_WITH_FEATURES)
    print(f"  {len(df)} rows")
    
    thresholds = calculate_thresholds(df)
    payload = {"n_stdev": N_STDEV, "thresholds": thresholds}
    
    config.WORDDOC_EXCLUSION_THRESHOLDS.parent.mkdir(parents=True, exist_ok=True)
    with open(config.WORDDOC_EXCLUSION_THRESHOLDS, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    
    print(f"\nwrote {config.WORDDOC_EXCLUSION_THRESHOLDS}\n")
    for column, stats in thresholds.items():
        print(f"  {column}: [{stats['lower']:.3f}, {stats['upper']:.3f}]  "
              f"(linear mean={stats['mean']:.3f}, std={stats['std']:.3f})")


if __name__ == "__main__":
    main()
