from typing import Dict, Any, List, Optional, Set
import pandas as pd
from app.services.profiler import detect_column_type
from app.services.detection.anomaly_detector import is_identifier_or_discrete_code


def generate_quality_heatmap(
    df: pd.DataFrame,
    issues: List[Dict[str, Any]],
    total_rows: int
) -> List[Dict[str, Any]]:
    """
    Generate deterministic, column-level data quality heatmap matrix across all five
    quality dimensions: missing values, invalid formats, duplicates, inconsistencies, and anomalies.

    Guarantees:
    - Zero fabrication of numbers or metrics.
    - True set union of row indices to avoid double counting.
    - Proper 'N/A' representation for non-applicable categories (e.g. anomalies in string columns).
    - Fully supports arbitrary columns, empty columns, and clean datasets.
    """
    heatmap: List[Dict[str, Any]] = []
    if total_rows == 0 and len(df.columns) == 0:
        return heatmap

    # Extract all dataset-level duplicate issues
    duplicate_issues = [i for i in issues if i.get("category") == "duplicate"]
    has_exact_duplicates = any("Exact Duplicate" in i.get("title", "") for i in duplicate_issues)
    feature_only_dup_issue = next(
        (i for i in duplicate_issues if i.get("metadata", {}).get("is_feature_only", False)),
        None
    )

    for col in df.columns:
        col_str = str(col)
        series = df[col]
        col_type = detect_column_type(series)
        is_numeric = pd.api.types.is_numeric_dtype(series)
        is_id_column = any(keyword in col_str.lower() for keyword in ["id", "key", "code", "uuid", "row_id", "_id"])

        # Filter issues associated specifically with this column
        col_issues = [i for i in issues if i.get("column") == col_str]

        # -------------------------------------------------------------
        # 1. Missing Values
        # -------------------------------------------------------------
        missing_iss = [i for i in col_issues if i.get("category") == "missing_value"]
        missing_rows: Set[int] = set()
        missing_ids: List[str] = []
        for mi in missing_iss:
            missing_rows.update(mi.get("row_indices", []))
            if mi.get("id"):
                missing_ids.append(mi["id"])

        missing_count = len(missing_rows)
        missing_pct = round((missing_count / total_rows) * 100, 1) if total_rows > 0 else 0.0
        missing_sev = "healthy"
        if missing_pct > 20.0:
            missing_sev = "high"
        elif missing_pct > 5.0:
            missing_sev = "moderate"
        elif missing_pct > 0.0:
            missing_sev = "low"

        cell_missing = {
            "category": "missing_value",
            "category_label": "Missing Values",
            "is_applicable": True,
            "percentage": missing_pct,
            "affected_count": missing_count,
            "severity": missing_sev,
            "issue_ids": missing_ids,
            "affected_rows": sorted(list(missing_rows)),
            "sample_values": ["<null/empty>"] if missing_count > 0 else [],
            "description": (
                f"{missing_count} missing or empty cell(s) ({missing_pct}%) in '{col_str}'."
                if missing_count > 0 else f"No missing values in '{col_str}'. 100% complete."
            ),
        }

        # -------------------------------------------------------------
        # 2. Invalid Formats
        # -------------------------------------------------------------
        format_iss = [i for i in col_issues if i.get("category") == "invalid_format"]
        format_rows: Set[int] = set()
        format_ids: List[str] = []
        format_samples: List[Any] = []
        for fi in format_iss:
            format_rows.update(fi.get("row_indices", []))
            if fi.get("id"):
                format_ids.append(fi["id"])
            format_samples.extend(fi.get("sample_values", []))

        format_count = len(format_rows)
        format_pct = round((format_count / total_rows) * 100, 1) if total_rows > 0 else 0.0
        format_sev = "healthy"
        if format_pct > 20.0:
            format_sev = "high"
        elif format_pct > 5.0:
            format_sev = "moderate"
        elif format_pct > 0.0:
            format_sev = "low"

        cell_format = {
            "category": "invalid_format",
            "category_label": "Invalid Formats",
            "is_applicable": True,
            "percentage": format_pct,
            "affected_count": format_count,
            "severity": format_sev,
            "issue_ids": format_ids,
            "affected_rows": sorted(list(format_rows)),
            "sample_values": format_samples[:5],
            "description": (
                f"{format_count} value(s) with invalid format ({format_pct}%) in '{col_str}'."
                if format_count > 0 else f"All checked values in '{col_str}' conform to valid syntax."
            ),
        }

        # -------------------------------------------------------------
        # 3. Categorical Inconsistencies
        # -------------------------------------------------------------
        incon_iss = [i for i in col_issues if i.get("category") == "inconsistency"]
        if is_numeric and not incon_iss:
            cell_inconsistency = {
                "category": "inconsistency",
                "category_label": "Categorical Inconsistencies",
                "is_applicable": False,
                "percentage": None,
                "affected_count": 0,
                "severity": "na",
                "issue_ids": [],
                "affected_rows": [],
                "sample_values": [],
                "description": f"Categorical consistency analysis is not applicable to numeric column '{col_str}'.",
            }
        else:
            incon_rows: Set[int] = set()
            incon_ids: List[str] = []
            incon_samples: List[Any] = []
            for ii in incon_iss:
                incon_rows.update(ii.get("row_indices", []))
                if ii.get("id"):
                    incon_ids.append(ii["id"])
                incon_samples.extend(ii.get("sample_values", []))

            incon_count = len(incon_rows)
            incon_pct = round((incon_count / total_rows) * 100, 1) if total_rows > 0 else 0.0
            incon_sev = "healthy"
            if incon_pct > 20.0:
                incon_sev = "high"
            elif incon_pct > 5.0:
                incon_sev = "moderate"
            elif incon_pct > 0.0:
                incon_sev = "low"

            cell_inconsistency = {
                "category": "inconsistency",
                "category_label": "Categorical Inconsistencies",
                "is_applicable": True,
                "percentage": incon_pct,
                "affected_count": incon_count,
                "severity": incon_sev,
                "issue_ids": incon_ids,
                "affected_rows": sorted(list(incon_rows)),
                "sample_values": incon_samples[:5],
                "description": (
                    f"{incon_count} value(s) with inconsistent casing or spacing ({incon_pct}%) in '{col_str}'."
                    if incon_count > 0 else f"No categorical casing inconsistencies detected in '{col_str}'."
                ),
            }

        # -------------------------------------------------------------
        # 4. Statistical Anomalies
        # -------------------------------------------------------------
        anomaly_iss = [i for i in col_issues if i.get("category") == "statistical_anomaly"]
        is_id_or_code = is_identifier_or_discrete_code(col_str, series)

        if (not is_numeric or is_id_or_code) and not anomaly_iss:
            cell_anomaly = {
                "category": "statistical_anomaly",
                "category_label": "Statistical Anomalies",
                "is_applicable": False,
                "percentage": None,
                "affected_count": 0,
                "severity": "na",
                "issue_ids": [],
                "affected_rows": [],
                "sample_values": [],
                "description": (
                    f"Statistical outlier detection is not applicable to identifier/code column '{col_str}'."
                    if is_id_or_code else "Statistical outlier detection (IQR/Z-score) is only applicable to continuous numeric columns."
                ),
            }
        else:
            anomaly_rows: Set[int] = set()
            anomaly_ids: List[str] = []
            anomaly_samples: List[Any] = []
            for ai in anomaly_iss:
                anomaly_rows.update(ai.get("row_indices", []))
                if ai.get("id"):
                    anomaly_ids.append(ai["id"])
                anomaly_samples.extend(ai.get("sample_values", []))

            anomaly_count = len(anomaly_rows)
            anomaly_pct = round((anomaly_count / total_rows) * 100, 1) if total_rows > 0 else 0.0
            anomaly_sev = "healthy"
            if anomaly_pct > 20.0:
                anomaly_sev = "high"
            elif anomaly_pct > 5.0:
                anomaly_sev = "moderate"
            elif anomaly_pct > 0.0:
                anomaly_sev = "low"

            cell_anomaly = {
                "category": "statistical_anomaly",
                "category_label": "Statistical Anomalies",
                "is_applicable": True,
                "percentage": anomaly_pct,
                "affected_count": anomaly_count,
                "severity": anomaly_sev,
                "issue_ids": anomaly_ids,
                "affected_rows": sorted(list(anomaly_rows)),
                "sample_values": anomaly_samples[:5],
                "description": (
                    f"{anomaly_count} statistical outlier(s) ({anomaly_pct}%) detected in '{col_str}'."
                    if anomaly_count > 0 else f"No extreme statistical outliers detected in '{col_str}'."
                ),
            }

        # -------------------------------------------------------------
        # 5. Duplicate Involvement
        # -------------------------------------------------------------
        # Determine whether this column is part of duplicate row records
        is_involved_in_duplicates = False
        dup_rows: Set[int] = set()
        dup_ids: List[str] = []

        if duplicate_issues:
            if has_exact_duplicates:
                is_involved_in_duplicates = True
                for di in duplicate_issues:
                    dup_rows.update(di.get("row_indices", []))
                    if di.get("id"):
                        dup_ids.append(di["id"])
            elif feature_only_dup_issue:
                # If feature-only duplicates, ID columns are unique and not involved
                if not is_id_column:
                    is_involved_in_duplicates = True
                    dup_rows.update(feature_only_dup_issue.get("row_indices", []))
                    if feature_only_dup_issue.get("id"):
                        dup_ids.append(feature_only_dup_issue["id"])

        dup_count = len(dup_rows) if is_involved_in_duplicates else 0
        dup_pct = round((dup_count / total_rows) * 100, 1) if total_rows > 0 else 0.0
        dup_sev = "healthy"
        if dup_pct > 20.0:
            dup_sev = "high"
        elif dup_pct > 5.0:
            dup_sev = "moderate"
        elif dup_pct > 0.0:
            dup_sev = "low"

        cell_duplicate = {
            "category": "duplicate",
            "category_label": "Duplicate Involvement",
            "is_applicable": True,
            "percentage": dup_pct,
            "affected_count": dup_count,
            "severity": dup_sev,
            "issue_ids": dup_ids,
            "affected_rows": sorted(list(dup_rows)),
            "sample_values": [],
            "description": (
                f"Column '{col_str}' is involved in {dup_count} duplicate record(s) ({dup_pct}% of dataset)."
                if dup_count > 0 else (
                    f"Column '{col_str}' is a unique identifier excluded from duplication."
                    if is_id_column and duplicate_issues else f"0% duplicate involvement in '{col_str}'."
                )
            ),
        }

        # -------------------------------------------------------------
        # Overall Column Quality Status
        # -------------------------------------------------------------
        all_cells = [cell_missing, cell_format, cell_inconsistency, cell_anomaly, cell_duplicate]
        applicable_severities = [c["severity"] for c in all_cells if c["is_applicable"]]

        if "high" in applicable_severities:
            overall_status = "high"
            overall_label = "High Severity"
        elif "moderate" in applicable_severities:
            overall_status = "moderate"
            overall_label = "Moderate Severity"
        elif "low" in applicable_severities:
            overall_status = "low"
            overall_label = "Low Severity"
        else:
            overall_status = "healthy"
            overall_label = "Healthy"

        # Unique count of issues impacting this column
        column_issue_ids: Set[str] = set()
        for c in all_cells:
            column_issue_ids.update(c["issue_ids"])

        heatmap.append({
            "column_name": col_str,
            "data_type": col_type,
            "is_numeric": is_numeric,
            "overall_status": overall_status,
            "overall_label": overall_label,
            "total_issues_count": len(column_issue_ids),
            "cells": {
                "missing_value": cell_missing,
                "invalid_format": cell_format,
                "inconsistency": cell_inconsistency,
                "statistical_anomaly": cell_anomaly,
                "duplicate": cell_duplicate,
            },
        })

    return heatmap
