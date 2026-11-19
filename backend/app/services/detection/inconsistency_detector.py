import re
from typing import List, Dict, Set, Tuple, Any
from collections import Counter
import pandas as pd
from app.services.detection.base import QualityIssue


def normalize_category_key(text: str) -> str:
    """Normalize string by removing leading/trailing spaces, collapsing internal spaces, and lowercasing."""
    # Collapse multiple spaces and dashes
    s = re.sub(r'[\s\-_]+', ' ', text).strip().lower()
    return s


def detect_inconsistencies(df: pd.DataFrame) -> List[QualityIssue]:
    """
    Identify inconsistent categorical values (e.g. Bangalore, bangalore, BANGALORE).
    Suggests possible standardizations without modifying any underlying data.
    """
    issues: List[QualityIssue] = []
    total_rows = len(df)
    if total_rows == 0:
        return issues

    for col in df.columns:
        series = df[col]
        # Only examine object or string columns
        if series.dtype != "object" and not pd.api.types.is_string_dtype(series):
            continue

        non_null = series.dropna().astype(str)
        if non_null.empty:
            continue

        # Skip columns that are likely unique identifiers (e.g. > 90% unique values)
        unique_ratio = non_null.nunique() / len(non_null)
        if unique_ratio > 0.85 and len(non_null) > 10:
            continue

        # Group values by normalized key
        # Maps normalized_key -> list of (row_1_indexed, raw_value)
        groups: Dict[str, List[Tuple[int, str]]] = {}
        for idx, val in enumerate(series):
            if pd.isna(val):
                continue
            val_str = str(val).strip()
            if not val_str:
                continue
            norm_key = normalize_category_key(val_str)
            if norm_key:
                groups.setdefault(norm_key, []).append((idx + 1, str(val)))

        # Find groups that have multiple distinct representations
        col_inconsistency_rows: List[int] = []
        inconsistent_clusters: List[Dict[str, Any]] = []

        for norm_key, occurrences in groups.items():
            distinct_raw = set(item[1] for item in occurrences)
            if len(distinct_raw) > 1:
                # Multiple distinct variants found for the same semantic category!
                counts = Counter(item[1] for item in occurrences)
                # Find most frequent variant as standard recommendation
                most_frequent, max_count = counts.most_common(1)[0]

                # If all have equal counts, prefer Title Case
                if max_count == 1:
                    title_candidate = norm_key.title()
                    # Check if title candidate is one of the variants
                    if title_candidate in distinct_raw:
                        standard_rec = title_candidate
                    else:
                        standard_rec = most_frequent
                else:
                    standard_rec = most_frequent

                cluster_rows = [item[0] for item in occurrences]
                col_inconsistency_rows.extend(cluster_rows)

                inconsistent_clusters.append({
                    "normalized_key": norm_key,
                    "distinct_variations": list(distinct_raw),
                    "distribution": [{"variant": v, "count": cnt} for v, cnt in counts.items()],
                    "suggested_standard": standard_rec,
                    "row_count": len(cluster_rows),
                    "rows": cluster_rows,
                })

        if inconsistent_clusters:
            unique_affected_rows = sorted(list(set(col_inconsistency_rows)))
            pct = round((len(unique_affected_rows) / total_rows) * 100, 2)

            # Build human-readable descriptions of top clusters
            cluster_summaries = []
            for c in inconsistent_clusters[:3]:
                variants_formatted = ", ".join(f"'{item['variant']}' ({item['count']})" for item in c["distribution"][:4])
                cluster_summaries.append(
                    f"{len(c['distinct_variations'])} variants of '{c['suggested_standard']}' [{variants_formatted}]"
                )

            summary_text = "; ".join(cluster_summaries)
            if len(inconsistent_clusters) > 3:
                summary_text += f"; and {len(inconsistent_clusters) - 3} more category set(s)"

            suggestions = [
                f"{c['distinct_variations']} -> '{c['suggested_standard']}'"
                for c in inconsistent_clusters[:3]
            ]
            action_text = f"Standardize categorical representations: {', '.join(suggestions)}."

            issues.append(
                QualityIssue(
                    id="",
                    category="inconsistency",
                    severity="warning",
                    column=str(col),
                    title=f"Inconsistent Categorical Values in '{col}'",
                    description=(
                        f"Detected {len(inconsistent_clusters)} inconsistent categorical cluster(s) "
                        f"affecting {len(unique_affected_rows)} row(s) ({pct}%). {summary_text}."
                    ),
                    row_indices=unique_affected_rows,
                    affected_count=len(unique_affected_rows),
                    sample_values=[c["distinct_variations"] for c in inconsistent_clusters[:4]],
                    suggested_action=action_text,
                    metadata={
                        "cluster_count": len(inconsistent_clusters),
                        "clusters": inconsistent_clusters[:15],
                    },
                )
            )

    return issues
