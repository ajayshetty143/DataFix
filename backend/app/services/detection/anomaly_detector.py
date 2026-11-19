import math
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np
from app.services.detection.base import QualityIssue


def detect_statistical_anomalies(df: pd.DataFrame) -> List[QualityIssue]:
    """
    Detect statistical outliers and anomalies in numerical columns using IQR and Z-Score.
    Safely handles small datasets and constant columns.
    Flags anomalies for human inspection rather than treating them automatically as errors.
    """
    issues: List[QualityIssue] = []
    total_rows = len(df)
    if total_rows < 4:
        # Small dataset safeguard: statistical distributions are not reliable with < 4 points
        return issues

    for col in df.columns:
        series = df[col]

        # Extract numeric series
        if not pd.api.types.is_numeric_dtype(series):
            # Attempt numeric coercion only if column is mostly numeric
            numeric_coerced = pd.to_numeric(series, errors="coerce")
            if numeric_coerced.notna().sum() < 4 or (numeric_coerced.notna().sum() / total_rows) < 0.6:
                continue
            num_series = numeric_coerced
        else:
            num_series = series

        valid_mask = num_series.notna()
        valid_count = int(valid_mask.sum())
        if valid_count < 4:
            continue

        clean_vals = num_series[valid_mask].astype(float)

        # Constant column safeguard: if standard deviation is 0, no anomalies exist
        std_val = float(clean_vals.std())
        if std_val == 0.0 or math.isnan(std_val):
            continue

        mean_val = float(clean_vals.mean())

        # 1. IQR Method
        q1 = float(clean_vals.quantile(0.25))
        q3 = float(clean_vals.quantile(0.75))
        iqr = q3 - q1

        # Calculate bounds
        lower_bound = q1 - 1.5 * iqr if iqr > 0 else mean_val - 3 * std_val
        upper_bound = q3 + 1.5 * iqr if iqr > 0 else mean_val + 3 * std_val
        extreme_lower = q1 - 3.0 * iqr if iqr > 0 else mean_val - 4 * std_val
        extreme_upper = q3 + 3.0 * iqr if iqr > 0 else mean_val + 4 * std_val

        # 2. Iterate through series and evaluate each point
        anomalous_rows: List[int] = []
        anomaly_details: List[Dict[str, Any]] = []
        has_extreme = False

        for idx, val in enumerate(num_series):
            if pd.isna(val):
                continue
            val_float = float(val)

            # Calculate Z-score
            z_score = abs((val_float - mean_val) / std_val) if std_val > 0 else 0.0

            # Condition: outside IQR bounds OR |Z| > 3.0
            is_iqr_outlier = val_float < lower_bound or val_float > upper_bound
            is_z_outlier = z_score >= 3.0

            if is_iqr_outlier or is_z_outlier:
                row_num = idx + 1
                anomalous_rows.append(row_num)

                is_extreme = (val_float < extreme_lower or val_float > extreme_upper or z_score >= 4.0)
                if is_extreme:
                    has_extreme = True

                anomaly_details.append({
                    "row": row_num,
                    "value": round(val_float, 4),
                    "z_score": round(z_score, 2),
                    "is_extreme": is_extreme,
                    "bound_violation": "below_lower" if val_float < lower_bound else "above_upper",
                })

        if anomalous_rows:
            pct = round((len(anomalous_rows) / total_rows) * 100, 2)
            # Label as 'warning' if extreme outliers exist, else 'info'
            severity = "warning" if has_extreme else "info"

            # Sample anomalous values for inspection
            sample_strings = [
                f"Row {a['row']}: {a['value']} (Z={a['z_score']}, {'Extreme' if a['is_extreme'] else 'Mild'})"
                for a in anomaly_details[:5]
            ]

            issues.append(
                QualityIssue(
                    id="",
                    category="statistical_anomaly",
                    severity=severity,
                    column=str(col),
                    title=f"Statistical Anomalies in '{col}'",
                    description=(
                        f"Detected {len(anomalous_rows)} statistical outlier(s) ({pct}%) in '{col}' "
                        f"outside expected bounds [{round(lower_bound, 2)}, {round(upper_bound, 2)}]. "
                        f"Distribution baseline: Mean={round(mean_val, 2)}, Std={round(std_val, 2)}, IQR={round(iqr, 2)}."
                    ),
                    row_indices=anomalous_rows,
                    affected_count=len(anomalous_rows),
                    sample_values=sample_strings,
                    suggested_action=(
                        "Inspect flagged outlier values to determine if they reflect rare genuine extremes "
                        "or measurement/entry errors requiring trimming or capping."
                    ),
                    metadata={
                        "outlier_count": len(anomalous_rows),
                        "outlier_percentage": pct,
                        "mean": round(mean_val, 4),
                        "std": round(std_val, 4),
                        "q1": round(q1, 4),
                        "q3": round(q3, 4),
                        "iqr": round(iqr, 4),
                        "lower_bound": round(lower_bound, 4),
                        "upper_bound": round(upper_bound, 4),
                        "extreme_count": sum(1 for a in anomaly_details if a["is_extreme"]),
                        "anomalies": anomaly_details[:30],
                    },
                )
            )

    return issues
