import re
from typing import List, Dict, Set, Tuple, Any
from collections import Counter
import pandas as pd
from app.services.detection.base import QualityIssue


def normalize_category_key(text: str) -> str:
    """Normalize string by removing leading/trailing spaces, collapsing internal spaces, and lowercasing."""
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

    for col_idx in range(len(df.columns)):
        series = df.iloc[:, col_idx]
        col = df.columns[col_idx]

        # Only examine object or string columns
        if series.dtype != "object" and not pd.api.types.is_string_dtype(series):
            continue

        non_null = series.dropna().astype(str)
        if non_null.empty:
            continue

        # Skip columns that are likely unique identifiers (e.g. > 85% unique values)
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

                # Deterministic canonical rule:
                # 1. Variant with highest frequency
                # 2. In case of ties, prefer title-cased key if present
                # 3. Deterministic alphabetical tie-break
                max_count = max(counts.values())
                candidates = [v for v, cnt in counts.items() if cnt == max_count]

                if len(candidates) == 1:
                    standard_rec = candidates[0]
                else:
                    title_candidate = norm_key.title()
                    matching_title = [c for c in candidates if c.strip() == title_candidate]
                    if matching_title:
                        standard_rec = matching_title[0]
                    else:
                        standard_rec = sorted(candidates, key=lambda s: (len(s.strip()), s))[0]

                # Count ONLY rows whose actual values differ from the canonical representation
                affected_cluster_rows = [item[0] for item in occurrences if item[1] != standard_rec]
                non_canonical_variants = [v for v in distinct_raw if v != standard_rec]

                # Keep all cluster variants available as diagnostic evidence
                if affected_cluster_rows:
                    col_inconsistency_rows.extend(affected_cluster_rows)

                    inconsistent_clusters.append({
                        "normalized_key": norm_key,
                        "canonical": standard_rec,
                        "suggested_standard": standard_rec,
                        "distinct_variations": sorted(list(distinct_raw)),
                        "non_canonical_variations": sorted(non_canonical_variants),
                        "distribution": [{"variant": v, "count": cnt} for v, cnt in counts.most_common()],
                        "total_cluster_rows": len(occurrences),
                        "affected_row_count": len(affected_cluster_rows),
                        "rows": affected_cluster_rows,
                        "all_rows": [item[0] for item in occurrences],
                    })

        if inconsistent_clusters:
            unique_affected_rows = sorted(list(set(col_inconsistency_rows)))
            pct = round((len(unique_affected_rows) / total_rows) * 100, 2)

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

            # Collect non-canonical values as problematic samples
            problematic_samples = []
            for c in inconsistent_clusters:
                for v in c["non_canonical_variations"]:
                    if v not in problematic_samples:
                        problematic_samples.append(v)

            issues.append(
                QualityIssue(
                    id="",
                    category="inconsistency",
                    severity="warning",
                    column=str(col),
                    title=f"Inconsistent Categorical Values in '{col}'",
                    description=(
                        f"Detected {len(inconsistent_clusters)} inconsistent categorical cluster(s) "
                        f"affecting {len(unique_affected_rows)} non-canonical row(s) ({pct}%). {summary_text}."
                    ),
                    row_indices=unique_affected_rows,
                    affected_count=len(unique_affected_rows),
                    sample_values=problematic_samples[:6],
                    suggested_action=action_text,
                    metadata={
                        "cluster_count": len(inconsistent_clusters),
                        "clusters": inconsistent_clusters[:15],
                    },
                )
            )

    return issues
