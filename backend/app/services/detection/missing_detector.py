from typing import List, Set
import pandas as pd
from app.services.detection.base import QualityIssue

# Common textual placeholders that represent missing data
MISSING_PLACEHOLDERS: Set[str] = {
    "n/a", "na", "null", "none", "nan", "nil", "undefined",
    "-", "--", "---", "?", "???", "missing", "unknown", "empty"
}


def detect_missing_values(df: pd.DataFrame) -> List[QualityIssue]:
    """
    Detect null, empty, whitespace-only, and placeholder values across all columns.
    Returns structured QualityIssue instances with exact 1-based row references.
    """
    issues: List[QualityIssue] = []
    total_rows = len(df)
    if total_rows == 0:
        return issues

    for col in df.columns:
        series = df[col]
        null_mask = series.isna()

        empty_indices: List[int] = []
        whitespace_indices: List[int] = []
        placeholder_indices: List[int] = []
        null_indices: List[int] = [i + 1 for i, is_null in enumerate(null_mask) if is_null]

        # Check non-null string values for empty, whitespace, and placeholders
        for idx, val in enumerate(series):
            if null_mask.iloc[idx]:
                continue

            if isinstance(val, str):
                trimmed = val.strip()
                if len(val) == 0:
                    empty_indices.append(idx + 1)
                elif len(trimmed) == 0:
                    whitespace_indices.append(idx + 1)
                elif trimmed.lower() in MISSING_PLACEHOLDERS:
                    placeholder_indices.append(idx + 1)

        all_missing_rows = sorted(list(set(
            null_indices + empty_indices + whitespace_indices + placeholder_indices
        )))

        total_missing = len(all_missing_rows)
        if total_missing == 0:
            continue

        pct = round((total_missing / total_rows) * 100, 2)

        # Determine severity based on data quality impact
        if pct >= 50.0:
            severity = "critical"
        elif pct >= 15.0:
            severity = "warning"
        else:
            severity = "info"

        breakdown = []
        if null_indices:
            breakdown.append(f"{len(null_indices)} null")
        if empty_indices:
            breakdown.append(f"{len(empty_indices)} empty string(s)")
        if whitespace_indices:
            breakdown.append(f"{len(whitespace_indices)} whitespace-only")
        if placeholder_indices:
            breakdown.append(f"{len(placeholder_indices)} placeholder(s)")

        breakdown_str = ", ".join(breakdown)

        sample_vals = []
        if null_indices:
            sample_vals.append("null")
        if whitespace_indices:
            sample_vals.append("'   '")
        if placeholder_indices:
            # Get up to 2 distinct placeholder representations
            seen_ph = list(set(str(series.iloc[i - 1]).strip() for i in placeholder_indices[:5]))
            sample_vals.extend(seen_ph[:2])

        issues.append(
            QualityIssue(
                id="",  # Assigned by engine
                category="missing_value",
                severity=severity,
                column=str(col),
                title=f"Missing Values in '{col}'",
                description=(
                    f"Found {total_missing} missing/blank value(s) ({pct}%) in column '{col}'. "
                    f"Breakdown: {breakdown_str}."
                ),
                row_indices=all_missing_rows,
                affected_count=total_missing,
                sample_values=sample_vals,
                suggested_action=(
                    "Evaluate whether to impute missing entries (mean/median for numerical, mode for categorical) "
                    "or drop rows where completeness is mandatory."
                ),
                metadata={
                    "total_missing": total_missing,
                    "missing_percentage": pct,
                    "null_count": len(null_indices),
                    "empty_count": len(empty_indices),
                    "whitespace_count": len(whitespace_indices),
                    "placeholder_count": len(placeholder_indices),
                },
            )
        )

    return issues
