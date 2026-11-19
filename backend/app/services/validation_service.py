import os
import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dataset import Dataset
from app.models.repair import RepairRecord
from app.services.dataset_service import (
    get_dataset_record,
    load_dataframe_from_file,
)
from app.services.detection.engine import QualityDetectionEngine

logger = logging.getLogger(__name__)


class ValidationService:
    """
    Deterministic Validation, Modification Audit Log, and Cleaned Data Export Service.
    Compares pre-repair and post-repair quality metrics, tracks all record alterations,
    and formats verified export packages.
    """

    @classmethod
    def validate_repairs(
        cls, db: Session, dataset_id: str, force_recompute: bool = False
    ) -> Dict[str, Any]:
        """
        Validate applied repairs by executing deterministic quality detection
        on the repaired working dataset and comparing against baseline metrics.
        """
        record = get_dataset_record(db, dataset_id)

        # 1. Verify that repaired file exists
        if not record.repaired_file_path or not os.path.exists(record.repaired_file_path):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No repaired working dataset exists yet. Please approve and apply repairs first.",
            )

        # 2. Return cached validation if available and not forced
        if not force_recompute and record.validation_json:
            try:
                return json.loads(record.validation_json)
            except Exception:
                pass

        # 3. Retrieve or compute original baseline quality report
        if record.quality_json:
            try:
                orig_quality = json.loads(record.quality_json)
            except Exception:
                orig_quality = None
        else:
            orig_quality = None

        if not orig_quality:
            df_orig = load_dataframe_from_file(record.file_path, record.file_type)
            orig_quality = QualityDetectionEngine.analyze(
                df=df_orig,
                dataset_id=record.id,
                filename=record.filename,
            )
            record.quality_json = json.dumps(orig_quality)
            db.commit()

        orig_summary = orig_quality.get("summary", {})
        orig_score = float(orig_summary.get("quality_score", 0.0))
        orig_issues = orig_summary.get("issues", [])

        # 4. Run detection engine on the repaired working copy
        df_repaired = load_dataframe_from_file(record.repaired_file_path, record.file_type)
        repaired_quality = QualityDetectionEngine.analyze(
            df=df_repaired,
            dataset_id=record.id,
            filename=f"repaired_{record.filename}",
        )
        repaired_summary = repaired_quality.get("summary", {})
        repaired_score = float(repaired_summary.get("quality_score", 0.0))
        repaired_issues = repaired_summary.get("issues", [])

        # 5. Determine resolved vs remaining issues
        # An issue is classified as resolved if its (category, column) is no longer flagged,
        # or if its affected count has dropped to 0.
        resolved_issues: List[Dict[str, Any]] = []
        repaired_issue_map: Dict[tuple, Dict[str, Any]] = {}
        for r_iss in repaired_issues:
            key = (r_iss.get("category"), r_iss.get("column"))
            repaired_issue_map[key] = r_iss

        orig_issue_by_key: Dict[tuple, str] = {}
        for orig_iss in orig_issues:
            cat = orig_iss.get("category")
            col = orig_iss.get("column")
            orig_count = orig_iss.get("affected_count", 0)
            key = (cat, col)
            orig_issue_by_key[key] = orig_iss.get("id", "UNKNOWN")

            if key not in repaired_issue_map:
                # Fully resolved!
                resolved_issues.append({
                    "issue_id": orig_iss.get("id", "UNKNOWN"),
                    "category": cat,
                    "column": col,
                    "title": orig_iss.get("title", ""),
                    "description": orig_iss.get("description", ""),
                    "resolved_count": orig_count,
                    "original_affected_count": orig_count,
                    "status": "fully_resolved",
                })
            else:
                remaining_matching = repaired_issue_map[key]
                new_count = remaining_matching.get("affected_count", 0)
                if new_count < orig_count:
                    # Partially resolved
                    resolved_issues.append({
                        "issue_id": orig_iss.get("id", "UNKNOWN"),
                        "category": cat,
                        "column": col,
                        "title": orig_iss.get("title", ""),
                        "description": f"Reduced affected rows from {orig_count} to {new_count}.",
                        "resolved_count": orig_count - new_count,
                        "original_affected_count": orig_count,
                        "status": "partially_resolved",
                    })

        # Enrich remaining issues with original_issue_id to preserve baseline issue ID trace
        enriched_remaining_issues: List[Dict[str, Any]] = []
        for r_iss in repaired_issues:
            item = dict(r_iss)
            orig_id = orig_issue_by_key.get((r_iss.get("category"), r_iss.get("column")))
            item["original_issue_id"] = orig_id if orig_id else r_iss.get("id")
            enriched_remaining_issues.append(item)

        # 6. Fetch repair stats from database
        repairs = (
            db.query(RepairRecord)
            .filter(RepairRecord.dataset_id == dataset_id)
            .all()
        )
        total_repairs = len(repairs)
        applied_repairs = sum(1 for r in repairs if r.status == "applied")
        rejected_repairs = sum(1 for r in repairs if r.status == "rejected")
        pending_repairs = sum(1 for r in repairs if r.status == "pending")
        failed_repairs = sum(1 for r in repairs if r.status == "failed")

        # 7. Construct complete validation comparison
        # Important: Never claim all issues are fixed unless remaining_issues count is 0
        is_fully_clean = len(enriched_remaining_issues) == 0

        report = {
            "dataset_id": dataset_id,
            "filename": record.filename,
            "original_quality_score": round(orig_score, 1),
            "repaired_quality_score": round(repaired_score, 1),
            "score_improvement": round(repaired_score - orig_score, 1),
            "is_fully_clean": is_fully_clean,
            "original_issues_count": len(orig_issues),
            "repaired_issues_count": len(enriched_remaining_issues),
            "resolved_issues_count": len(resolved_issues),
            "remaining_issues_count": len(enriched_remaining_issues),
            "resolved_issues": resolved_issues,
            "remaining_issues": enriched_remaining_issues,
            "repair_summary": {
                "total": total_repairs,
                "applied": applied_repairs,
                "rejected": rejected_repairs,
                "pending": pending_repairs,
                "failed": failed_repairs,
            },
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Cache validation result
        record.validation_json = json.dumps(report)
        db.commit()

        return report

    @classmethod
    def get_audit_log(cls, db: Session, dataset_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve structured modification audit log detailing every proposed,
        approved, rejected, or applied repair.
        """
        repairs = (
            db.query(RepairRecord)
            .filter(RepairRecord.dataset_id == dataset_id)
            .order_by(RepairRecord.row_index.asc(), RepairRecord.repair_id.asc())
            .all()
        )

        entries = []
        for r in repairs:
            # Timestamp priority: applied_at -> updated_at -> created_at
            ts = r.applied_at or r.updated_at or r.created_at
            applied_val = r.applied_value if r.status == "applied" else (r.proposed_value or "")

            entries.append({
                "repair_id": r.repair_id,
                "dataset_id": r.dataset_id,
                "issue_id": r.issue_id,
                "repair_type": r.repair_type,
                "column_name": r.column_name or "(Row-level)",
                "row_index": r.row_index,
                "row_number": r.row_index + 1,  # 1-indexed for human readability
                "original_value": r.original_value or "<empty>",
                "new_value": applied_val or "<none>",
                "status": r.status,
                "action": r.explanation,
                "confidence": r.confidence,
                "human_review_required": r.human_review_required,
                "timestamp": ts.isoformat() if ts else datetime.now(timezone.utc).isoformat(),
                "error_message": r.error_message,
            })

        return entries

    @classmethod
    def export_audit_log_csv(cls, db: Session, dataset_id: str) -> str:
        """Generate CSV string of the modification audit log."""
        entries = cls.get_audit_log(db, dataset_id)
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "Dataset ID",
            "Repair ID",
            "Issue ID",
            "Repair Type",
            "Column",
            "Row (1-indexed)",
            "Original Value",
            "New / Applied Value",
            "Status",
            "Action Description",
            "Confidence",
            "Human Review Required",
            "Timestamp",
            "Error Message",
        ])

        for e in entries:
            writer.writerow([
                e["dataset_id"],
                e["repair_id"],
                e["issue_id"],
                e["repair_type"],
                e["column_name"],
                e["row_number"],
                e["original_value"],
                e["new_value"],
                e["status"],
                e["action"],
                e["confidence"],
                "Yes" if e["human_review_required"] else "No",
                e["timestamp"],
                e["error_message"] or "",
            ])

        return output.getvalue()

    @classmethod
    def get_cleaned_csv_path(cls, db: Session, dataset_id: str) -> Tuple[str, str]:
        """
        Get absolute path to cleaned CSV file for export.
        If repaired file is Excel (.xlsx), automatically exports it to CSV without modifying original.
        Returns: (file_path, export_filename)
        """
        record = get_dataset_record(db, dataset_id)
        if not record.repaired_file_path or not os.path.exists(record.repaired_file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No cleaned dataset found. Please apply approved repairs before exporting.",
            )

        base_name = os.path.splitext(record.filename)[0]
        cleaned_filename = f"cleaned_{base_name}.csv"

        if record.file_type == "csv":
            return record.repaired_file_path, cleaned_filename

        # If Excel, convert to CSV for standardized export
        csv_export_path = os.path.join(
            settings.UPLOAD_DIR, f"{dataset_id}_cleaned_export.csv"
        )
        df_repaired = pd.read_excel(record.repaired_file_path, engine="openpyxl")
        df_repaired.to_csv(csv_export_path, index=False, encoding="utf-8")
        return csv_export_path, cleaned_filename

    @classmethod
    def generate_quality_report_dict(cls, db: Session, dataset_id: str) -> Dict[str, Any]:
        """
        Compile full comprehensive Data Quality Audit and Validation Report
        suitable for JSON export or executive presentation.
        """
        record = get_dataset_record(db, dataset_id)
        validation_data = cls.validate_repairs(db, dataset_id, force_recompute=False)
        audit_entries = cls.get_audit_log(db, dataset_id)

        return {
            "title": "DataFix Data Quality & Remediation Audit Report",
            "dataset": {
                "id": record.id,
                "filename": record.filename,
                "file_type": record.file_type,
                "original_rows": record.total_rows,
                "original_columns": record.total_columns,
                "created_at": record.created_at.isoformat(),
                "repaired_at": record.repaired_at.isoformat() if record.repaired_at else None,
            },
            "quality_comparison": {
                "original_score": validation_data["original_quality_score"],
                "repaired_score": validation_data["repaired_quality_score"],
                "score_improvement": validation_data["score_improvement"],
                "is_fully_clean": validation_data["is_fully_clean"],
                "original_issues_count": validation_data["original_issues_count"],
                "remaining_issues_count": validation_data["remaining_issues_count"],
                "resolved_issues_count": validation_data["resolved_issues_count"],
            },
            "repair_statistics": validation_data["repair_summary"],
            "resolved_issues": validation_data["resolved_issues"],
            "remaining_issues": validation_data["remaining_issues"],
            "audit_log": audit_entries,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }
