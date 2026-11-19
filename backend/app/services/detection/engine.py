from datetime import datetime, timezone
from typing import Dict, Any, List, Set
import pandas as pd

from app.services.detection.base import QualityIssue
from app.services.detection.missing_detector import detect_missing_values
from app.services.detection.duplicate_detector import detect_duplicates
from app.services.detection.format_detector import detect_invalid_formats
from app.services.detection.inconsistency_detector import detect_inconsistencies
from app.services.detection.anomaly_detector import detect_statistical_anomalies


class QualityDetectionEngine:
    """
    Central orchestration engine that executes modular data quality detection
    across all five key dimensions and compiles structured analysis results.
    """

    @classmethod
    def analyze(
        cls, 
        df: pd.DataFrame, 
        dataset_id: str, 
        filename: str
    ) -> Dict[str, Any]:
        raw_issues: List[QualityIssue] = []

        # 1. Missing Value Detection
        raw_issues.extend(detect_missing_values(df))

        # 2. Duplicate Detection
        raw_issues.extend(detect_duplicates(df))

        # 3. Invalid Format Detection
        raw_issues.extend(detect_invalid_formats(df))

        # 4. Inconsistency Detection
        raw_issues.extend(detect_inconsistencies(df))

        # 5. Statistical Anomaly Detection
        raw_issues.extend(detect_statistical_anomalies(df))

        # Assign deterministic, sequential issue IDs (ISS-001, ISS-002, ...)
        indexed_issues: List[Dict[str, Any]] = []
        all_affected_rows: Set[int] = set()
        all_affected_columns: Set[str] = set()

        by_category: Dict[str, int] = {
            "missing_value": 0,
            "duplicate": 0,
            "invalid_format": 0,
            "inconsistency": 0,
            "statistical_anomaly": 0,
        }

        by_severity: Dict[str, int] = {
            "critical": 0,
            "warning": 0,
            "info": 0,
        }

        for idx, issue in enumerate(raw_issues):
            issue.id = f"ISS-{idx + 1:03d}"
            issue_dict = issue.to_dict()
            indexed_issues.append(issue_dict)

            # Accumulate counts
            cat = issue.category
            if cat in by_category:
                by_category[cat] += 1
            else:
                by_category[cat] = 1

            sev = issue.severity
            if sev in by_severity:
                by_severity[sev] += 1
            else:
                by_severity[sev] = 1

            for r in issue.row_indices:
                all_affected_rows.add(r)

            if issue.column:
                all_affected_columns.add(issue.column)

        total_rows = len(df)
        total_cols = len(df.columns)
        total_issues = len(indexed_issues)

        # Deterministic Data Quality Score (0 to 100)
        # Factor 1: Clean rows ratio
        affected_rows_count = len(all_affected_rows)
        clean_rows_ratio = (
            (total_rows - affected_rows_count) / total_rows if total_rows > 0 else 1.0
        )

        # Factor 2: Severity deduction penalties
        severity_penalties = (
            (by_severity["critical"] * 12) +
            (by_severity["warning"] * 4) +
            (by_severity["info"] * 1)
        )

        # Weighted calculation
        raw_score = (clean_rows_ratio * 70.0) + max(0.0, (30.0 - severity_penalties))
        quality_score = round(max(0.0, min(100.0, raw_score)), 1) if total_rows > 0 else 100.0

        return {
            "dataset_id": dataset_id,
            "filename": filename,
            "total_rows": total_rows,
            "total_columns": total_cols,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_issues": total_issues,
                "total_affected_rows": affected_rows_count,
                "total_affected_columns": len(all_affected_columns),
                "quality_score": quality_score,
                "by_category": by_category,
                "by_severity": by_severity,
                "issues": indexed_issues,
            },
        }
