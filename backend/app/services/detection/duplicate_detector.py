from typing import List, Dict, Set, Any
import pandas as pd
from app.services.detection.base import QualityIssue


def detect_duplicates(df: pd.DataFrame) -> List[QualityIssue]:
    """
    Detect exact duplicate rows and potential near-duplicate records.
    Never modifies, drops, or merges records.
    """
    issues: List[QualityIssue] = []
    total_rows = len(df)
    if total_rows < 2:
        return issues

    # 1. Exact Duplicate Rows Detection across ALL columns
    exact_dup_mask = df.duplicated(keep=False)

    # Also check if rows are duplicate across all feature columns excluding an ID column
    id_cols = [c for c in df.columns if str(c).lower() in ("id", "row_id", "record_id", "_id", "uuid")]
    feature_dup_mask = pd.Series(False, index=df.index)
    if not exact_dup_mask.any() and id_cols and len(df.columns) > len(id_cols):
        feature_df = df.drop(columns=id_cols)
        feature_dup_mask = feature_df.duplicated(keep=False)

    dup_mask = exact_dup_mask if exact_dup_mask.any() else feature_dup_mask
    is_feature_only = (not exact_dup_mask.any()) and feature_dup_mask.any()

    if dup_mask.any():
        dup_indices = [i + 1 for i, is_dup in enumerate(dup_mask) if is_dup]
        total_dup_rows = len(dup_indices)

        # Cluster identical rows to show groupings
        check_df = df.drop(columns=id_cols) if is_feature_only else df
        clusters: Dict[tuple, List[int]] = {}
        for row_num in dup_indices:
            row_data = tuple(str(x) for x in check_df.iloc[row_num - 1].values)
            clusters.setdefault(row_data, []).append(row_num)

        sample_cluster_descriptions = []
        sample_rows_data = []
        for cluster_key, row_nums in list(clusters.items())[:3]:
            sample_cluster_descriptions.append(f"Rows [{', '.join(map(str, row_nums))}]")
            cols_to_show = [str(c) for c in check_df.columns[:4]]
            sample_rows_data.append(dict(zip(cols_to_show, [str(v)[:25] for v in cluster_key[:4]])))

        dup_pct = round((total_dup_rows / total_rows) * 100, 2)
        severity = "critical" if dup_pct >= 25.0 else "warning"

        title_prefix = "Exact Duplicate Records (Matching all features)" if is_feature_only else "Exact Duplicate Rows"

        issues.append(
            QualityIssue(
                id="",
                category="duplicate",
                severity=severity,
                column=None,
                title=f"{title_prefix} ({len(clusters)} group(s))",
                description=(
                    f"Found {total_dup_rows} duplicate rows ({dup_pct}%) across {len(clusters)} cluster(s). "
                    f"Identical groups: {'; '.join(sample_cluster_descriptions)}."
                ),
                row_indices=dup_indices,
                affected_count=total_dup_rows,
                sample_values=sample_rows_data,
                suggested_action=(
                    "Deduplicate records by preserving the earliest or most recent primary record."
                ),
                metadata={
                    "total_duplicate_rows": total_dup_rows,
                    "duplicate_percentage": dup_pct,
                    "cluster_count": len(clusters),
                    "is_feature_only": is_feature_only,
                    "clusters": {
                        f"cluster_{i+1}": rows
                        for i, rows in enumerate(list(clusters.values())[:20])
                    },
                },
            )
        )

    # 2. Potential / Near-Duplicate Detection (Casing & Whitespace Differences)
    str_col_indices = [
        i for i in range(len(df.columns))
        if df.iloc[:, i].dtype == "object" or isinstance(df.iloc[0, i] if len(df) > 0 else None, str)
    ]
    if str_col_indices:
        normalized_df = df.copy()
        for idx in str_col_indices:
            normalized_df.iloc[:, idx] = normalized_df.iloc[:, idx].astype(str).str.strip().str.lower()

        norm_dup_mask = normalized_df.duplicated(keep=False)
        near_dup_mask = norm_dup_mask & (~dup_mask)

        if near_dup_mask.any():
            near_dup_indices = [i + 1 for i, is_near in enumerate(near_dup_mask) if is_near]

            near_clusters: Dict[tuple, List[int]] = {}
            for row_num in near_dup_indices:
                row_key = tuple(str(x) for x in normalized_df.iloc[row_num - 1].values)
                near_clusters.setdefault(row_key, []).append(row_num)

            issues.append(
                QualityIssue(
                    id="",
                    category="duplicate",
                    severity="info",
                    column=None,
                    title=f"Potential Near-Duplicate Rows ({len(near_clusters)} group(s))",
                    description=(
                        f"Found {len(near_dup_indices)} row(s) that differ only in casing, padding, or subtle formatting."
                    ),
                    row_indices=near_dup_indices,
                    affected_count=len(near_dup_indices),
                    sample_values=[],
                    suggested_action="Review and standardize text normalization across these near-duplicate rows.",
                    metadata={
                        "near_duplicate_count": len(near_dup_indices),
                        "cluster_count": len(near_clusters),
                        "clusters": {
                            f"group_{i+1}": rows
                            for i, rows in enumerate(list(near_clusters.values())[:20])
                        },
                    },
                )
            )

    return issues
