import math
from typing import Dict, Any, List
import pandas as pd
import numpy as np


def format_file_size(size_bytes: int) -> str:
    """Format bytes into human-readable string (B, KB, MB, GB)."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def detect_column_type(series: pd.Series) -> str:
    """Detect intuitive semantic column data type."""
    dtype_str = str(series.dtype).lower()

    if "bool" in dtype_str:
        return "boolean"
    if "datetime" in dtype_str or "timestamp" in dtype_str:
        return "datetime"
    if "int" in dtype_str:
        return "integer"
    if "float" in dtype_str:
        # Check if all non-null values are effectively integers
        non_null = series.dropna()
        if not non_null.empty and (non_null % 1 == 0).all():
            return "integer"
        return "float"

    # For object/string dtypes, check if values could be datetime or boolean
    non_null = series.dropna().astype(str).str.strip()
    if non_null.empty:
        return "string"

    # Check for boolean text representations
    unique_vals = set(non_null.str.lower().unique())
    if unique_vals.issubset({"true", "false", "t", "f", "1", "0", "yes", "no"}):
        return "boolean"

    # Try datetime heuristic on sample if reasonable length
    sample = non_null.head(50)
    try:
        # Only attempt if not purely short numbers or pure strings
        if sample.str.contains(r"[-/:\s]", regex=True).any():
            pd.to_datetime(sample, errors="raise", format="mixed")
            return "datetime"
    except Exception:
        pass

    return "string"


def profile_dataframe(df: pd.DataFrame, file_size: int, filename: str, dataset_id: str) -> Dict[str, Any]:
    """Generate comprehensive dataset statistics and column profiles."""
    total_rows = len(df)
    total_columns = len(df.columns)
    columns = [str(col) for col in df.columns]

    column_profiles = []

    for col_idx in range(len(df.columns)):
        series = df.iloc[:, col_idx]
        col = df.columns[col_idx]
        col_type = detect_column_type(series)
        null_count = int(series.isna().sum())
        null_percentage = round((null_count / total_rows * 100), 2) if total_rows > 0 else 0.0
        unique_count = int(series.nunique(dropna=True))

        is_numerical = col_type in ("integer", "float") or pd.api.types.is_numeric_dtype(series)

        stats = None
        if is_numerical:
            num_series = pd.to_numeric(series, errors="coerce").dropna()
            # Also exclude infinite values from statistical aggregates
            num_series = num_series[np.isfinite(num_series)]
            if not num_series.empty:
                mean_val = float(num_series.mean())
                median_val = float(num_series.median())
                min_val = float(num_series.min())
                max_val = float(num_series.max())
                std_val = float(num_series.std()) if len(num_series) > 1 else 0.0

                stats = {
                    "mean": round(mean_val, 4) if not math.isnan(mean_val) else None,
                    "median": round(median_val, 4) if not math.isnan(median_val) else None,
                    "min": round(min_val, 4) if not math.isnan(min_val) else None,
                    "max": round(max_val, 4) if not math.isnan(max_val) else None,
                    "std": round(std_val, 4) if not math.isnan(std_val) else None,
                }

        # Collect small sample of non-null values for display
        sample_vals = []
        for val in series.dropna().head(3):
            if pd.isna(val):
                continue
            if isinstance(val, (np.integer, int)):
                sample_vals.append(int(val))
            elif isinstance(val, (np.floating, float)):
                if math.isfinite(val):
                    sample_vals.append(round(float(val), 4))
                else:
                    sample_vals.append(str(val))
            else:
                sample_vals.append(str(val))

        column_profiles.append({
            "name": str(col),
            "data_type": col_type,
            "null_count": null_count,
            "null_percentage": null_percentage,
            "unique_count": unique_count,
            "is_numerical": is_numerical,
            "stats": stats,
            "sample_values": sample_vals,
        })

    return {
        "id": dataset_id,
        "filename": filename,
        "file_size": file_size,
        "file_size_formatted": format_file_size(file_size),
        "total_rows": total_rows,
        "total_columns": total_columns,
        "columns": columns,
        "column_profiles": column_profiles,
    }
