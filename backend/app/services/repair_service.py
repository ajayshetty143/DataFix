import os
import re
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.dataset import Dataset
from app.models.repair import RepairRecord
from app.schemas.repair import (
    RepairResponse,
    RepairSummary,
    RepairListResponse,
    RepairResultItem,
    RepairApplyResponse,
)
from app.services.dataset_service import (
    get_dataset_record,
    load_dataframe_from_file,
    clean_row_value,
)
from app.services.profiler import detect_column_type
from app.services.detection.engine import QualityDetectionEngine

logger = logging.getLogger(__name__)


def clean_cell_str(val: Any) -> str:
    """Normalize cell value to clean string for deterministic comparison."""
    if pd.isna(val) or val is None:
        return ""
    val_str = str(val).strip()
    if val_str.lower() in ["nan", "none", "null", "<null>"]:
        return ""
    return val_str


class RepairService:
    """
    Deterministic Python-based safe data repair engine.
    Proposes, validates, approves, rejects, and applies repairs
    onto a separate working copy while keeping original files immutable.
    """

    @classmethod
    def propose_repairs(cls, db: Session, dataset_id: str) -> List[RepairRecord]:
        """
        Generate deterministic repair proposals from Phase 3 detection engine results
        and Phase 4 Gemini AI recommendations.
        """
        record = get_dataset_record(db, dataset_id)

        # 1. Ensure quality analysis exists
        if record.quality_json:
            try:
                quality_data = json.loads(record.quality_json)
            except Exception:
                quality_data = None
        else:
            quality_data = None

        if not quality_data:
            df_orig = load_dataframe_from_file(record.file_path, record.file_type)
            quality_data = QualityDetectionEngine.analyze(
                df=df_orig,
                dataset_id=record.id,
                filename=record.filename,
            )
            record.quality_json = json.dumps(quality_data)
            db.commit()

        # 2. Load DataFrame
        df = load_dataframe_from_file(record.file_path, record.file_type)

        # 3. Retrieve any existing repairs to preserve approved/applied status
        existing_repairs = (
            db.query(RepairRecord)
            .filter(RepairRecord.dataset_id == dataset_id)
            .all()
        )
        existing_map: Dict[Tuple[str, int, Optional[str]], RepairRecord] = {
            (r.issue_id, r.row_index, r.column_name): r
            for r in existing_repairs
        }

        # 4. Parse AI Detective recommendations for contextual explanations if available
        ai_recs_map: Dict[str, Dict[str, Any]] = {}
        if record.ai_detective_json:
            try:
                ai_data = json.loads(record.ai_detective_json)
                for item in ai_data.get("recommendations", []):
                    ai_recs_map[item.get("issue_id", "")] = item
            except Exception:
                pass

        issues = quality_data.get("summary", {}).get("issues", [])
        repairs_to_save: List[RepairRecord] = []
        counter = 1

        for issue in issues:
            issue_id = issue.get("id")
            category = issue.get("category")
            col_name = issue.get("column")
            raw_row_indices = issue.get("row_indices", [])
            # QualityIssue.row_indices contains 1-based row numbers.
            # Convert to 0-based dataframe indices for deterministic row tracking.
            row_indices = [r - 1 for r in raw_row_indices if r >= 1]
            metadata = issue.get("metadata", {})
            ai_rec = ai_recs_map.get(issue_id, {})

            # -----------------------------------------------------------------
            # CATEGORY 1: Missing Values
            # -----------------------------------------------------------------
            if category == "missing_value":
                is_numeric_col = False
                median_val_str: Optional[str] = None

                if col_name and col_name in df.columns:
                    col_series = df[col_name]
                    is_numeric_col = pd.api.types.is_numeric_dtype(col_series)
                    is_id_column = any(keyword in col_name.lower() for keyword in ["id", "key", "code", "uuid"])

                    if is_numeric_col and not is_id_column:
                        valid_nums = pd.to_numeric(col_series, errors="coerce").dropna()
                        if len(valid_nums) > 0:
                            med = valid_nums.median()
                            col_type = detect_column_type(col_series)
                            if col_type == "integer" or all(x.is_integer() for x in valid_nums):
                                median_val_str = str(int(round(med)))
                            else:
                                median_val_str = str(round(float(med), 4))

                for r in row_indices:
                    orig_val = clean_cell_str(df.at[r, col_name]) if (col_name and 0 <= r < len(df)) else ""
                    key = (issue_id, r, col_name)
                    if key in existing_map:
                        repairs_to_save.append(existing_map[key])
                        continue

                    if is_numeric_col and median_val_str is not None:
                        repair = RepairRecord(
                            repair_id=f"REP-{counter:03d}",
                            dataset_id=dataset_id,
                            issue_id=issue_id,
                            repair_type="missing_imputation",
                            column_name=col_name,
                            row_index=r,
                            original_value=orig_val or "<null>",
                            proposed_value=median_val_str,
                            explanation=f"Impute missing numeric value in '{col_name}' using column median ({median_val_str}). Preserves central distribution without bias.",
                            confidence="High",
                            human_review_required=False,
                            status="pending",
                        )
                    else:
                        repair = RepairRecord(
                            repair_id=f"REP-{counter:03d}",
                            dataset_id=dataset_id,
                            issue_id=issue_id,
                            repair_type="missing_imputation",
                            column_name=col_name,
                            row_index=r,
                            original_value=orig_val or "<null>",
                            proposed_value=None,  # Requires manual input
                            explanation=f"Missing value in '{col_name}' (non-numeric/identity column). Cannot be safely imputed. Manual domain input required.",
                            confidence="Low",
                            human_review_required=True,
                            status="pending",
                        )
                    counter += 1
                    repairs_to_save.append(repair)

            # -----------------------------------------------------------------
            # CATEGORY 2: Duplicate Records
            # -----------------------------------------------------------------
            elif category == "duplicate":
                # Deduplication: preserve the first unique record in each cluster, propose dropping redundant duplicates
                clusters_meta = metadata.get("clusters", {})
                if clusters_meta:
                    redundant_0indexed = []
                    for cluster_name, row_nums in clusters_meta.items():
                        # row_nums are 1-based row numbers: row_nums[0] is original, row_nums[1:] are duplicates
                        if isinstance(row_nums, list) and len(row_nums) > 1:
                            for r_num in row_nums[1:]:
                                if r_num >= 1:
                                    redundant_0indexed.append(r_num - 1)
                    target_dup_indices = sorted(list(set(redundant_0indexed)))
                else:
                    target_dup_indices = row_indices[1:] if len(row_indices) > 1 else []

                for r in target_dup_indices:
                    key = (issue_id, r, None)
                    if key in existing_map:
                        repairs_to_save.append(existing_map[key])
                        continue

                    repair = RepairRecord(
                        repair_id=f"REP-{counter:03d}",
                        dataset_id=dataset_id,
                        issue_id=issue_id,
                        repair_type="deduplication",
                        column_name=None,
                        row_index=r,
                        original_value=f"Duplicate row (Index {r})",
                        proposed_value="[REMOVE_DUPLICATE_ROW]",
                        explanation=f"Drop redundant duplicate row at index {r}, preserving the first unique occurrence in the dataset.",
                        confidence="High",
                        human_review_required=False,
                        status="pending",
                    )
                    counter += 1
                    repairs_to_save.append(repair)

            # -----------------------------------------------------------------
            # CATEGORY 3: Inconsistent Categories
            # -----------------------------------------------------------------
            elif category == "inconsistency":
                clusters_meta = metadata.get("clusters", [])
                if clusters_meta and isinstance(clusters_meta, list):
                    # Propose canonicalization per cluster
                    for c in clusters_meta:
                        std_val = c.get("suggested_standard")
                        cluster_rows_1based = c.get("rows", [])
                        for r_num in cluster_rows_1based:
                            if r_num < 1:
                                continue
                            r = r_num - 1
                            orig_val = clean_cell_str(df.at[r, col_name]) if (col_name and 0 <= r < len(df)) else ""
                            # If cell already matches canonical value, skip no-op repair
                            if std_val and orig_val.strip() == std_val.strip():
                                continue

                            key = (issue_id, r, col_name)
                            if key in existing_map:
                                repairs_to_save.append(existing_map[key])
                                continue

                            repair = RepairRecord(
                                repair_id=f"REP-{counter:03d}",
                                dataset_id=dataset_id,
                                issue_id=issue_id,
                                repair_type="category_normalization",
                                column_name=col_name,
                                row_index=r,
                                original_value=orig_val,
                                proposed_value=std_val,
                                explanation=f"Normalize casing and whitespace in '{col_name}' from '{orig_val}' to canonical category '{std_val}'.",
                                confidence="High",
                                human_review_required=False,
                                status="pending",
                            )
                            counter += 1
                            repairs_to_save.append(repair)
                else:
                    canonical = metadata.get("canonical")
                    if not canonical and col_name and col_name in df.columns:
                        non_nulls = df[col_name].dropna().astype(str).str.strip()
                        canonical = non_nulls.mode().iloc[0] if len(non_nulls) > 0 else None

                    for r in row_indices:
                        orig_val = clean_cell_str(df.at[r, col_name]) if (col_name and 0 <= r < len(df)) else ""
                        if canonical and orig_val.strip() == canonical.strip():
                            continue

                        key = (issue_id, r, col_name)
                        if key in existing_map:
                            repairs_to_save.append(existing_map[key])
                            continue

                        repair = RepairRecord(
                            repair_id=f"REP-{counter:03d}",
                            dataset_id=dataset_id,
                            issue_id=issue_id,
                            repair_type="category_normalization",
                            column_name=col_name,
                            row_index=r,
                            original_value=orig_val,
                            proposed_value=canonical,
                            explanation=f"Normalize casing and whitespace in '{col_name}' from '{orig_val}' to canonical category '{canonical}'.",
                            confidence="High",
                            human_review_required=False,
                            status="pending",
                        )
                        counter += 1
                        repairs_to_save.append(repair)

            # -----------------------------------------------------------------
            # CATEGORY 4: Invalid Formats
            # -----------------------------------------------------------------
            elif category == "invalid_format":
                for r in row_indices:
                    orig_val = clean_cell_str(df.at[r, col_name]) if (col_name and 0 <= r < len(df)) else ""
                    key = (issue_id, r, col_name)
                    if key in existing_map:
                        repairs_to_save.append(existing_map[key])
                        continue

                    # Check for unambiguous format fixes (e.g. whitespace around valid emails)
                    unambiguous_fix = None
                    if "@" in orig_val and re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", orig_val.strip()):
                        unambiguous_fix = orig_val.strip()

                    # Check date slashes e.g. 2024/05/12 -> 2024-05-12
                    if re.match(r"^\d{4}/\d{2}/\d{2}$", orig_val.strip()):
                        unambiguous_fix = orig_val.strip().replace("/", "-")

                    if unambiguous_fix and unambiguous_fix != orig_val:
                        repair = RepairRecord(
                            repair_id=f"REP-{counter:03d}",
                            dataset_id=dataset_id,
                            issue_id=issue_id,
                            repair_type="format_correction",
                            column_name=col_name,
                            row_index=r,
                            original_value=orig_val,
                            proposed_value=unambiguous_fix,
                            explanation=f"Unambiguous format correction in '{col_name}': standardized '{orig_val}' to '{unambiguous_fix}'.",
                            confidence="High",
                            human_review_required=False,
                            status="pending",
                        )
                    else:
                        repair = RepairRecord(
                            repair_id=f"REP-{counter:03d}",
                            dataset_id=dataset_id,
                            issue_id=issue_id,
                            repair_type="format_correction",
                            column_name=col_name,
                            row_index=r,
                            original_value=orig_val,
                            proposed_value=None,  # Requires manual review
                            explanation=f"Invalid format in '{col_name}' ('{orig_val}'). Cannot be safely guessed. Manual correction required.",
                            confidence="Low",
                            human_review_required=True,
                            status="pending",
                        )
                    counter += 1
                    repairs_to_save.append(repair)

            # -----------------------------------------------------------------
            # CATEGORY 5: Statistical Anomalies
            # -----------------------------------------------------------------
            elif category == "statistical_anomaly":
                for r in row_indices:
                    orig_val = clean_cell_str(df.at[r, col_name]) if (col_name and 0 <= r < len(df)) else ""
                    key = (issue_id, r, col_name)
                    if key in existing_map:
                        repairs_to_save.append(existing_map[key])
                        continue

                    # Outliers must NEVER be automatically capped or deleted without user review
                    repair = RepairRecord(
                        repair_id=f"REP-{counter:03d}",
                        dataset_id=dataset_id,
                        issue_id=issue_id,
                        repair_type="anomaly_review",
                        column_name=col_name,
                        row_index=r,
                        original_value=orig_val,
                        proposed_value=None,  # Do not invent replacement
                        explanation=f"Extreme statistical anomaly flagged in '{col_name}' (value: {orig_val}). Outliers may be genuine high-impact transactions; automated capping or deletion is prohibited. Explicit user review required.",
                        confidence="Low",
                        human_review_required=True,
                        status="pending",
                    )
                    counter += 1
                    repairs_to_save.append(repair)

        # 5. Save fresh proposals to DB
        # Remove any pending repairs not present in current proposals
        for rec in repairs_to_save:
            if not rec.id:
                db.add(rec)
        db.commit()

        return cls.get_repairs(db, dataset_id).repairs

    @classmethod
    def get_repairs(cls, db: Session, dataset_id: str) -> RepairListResponse:
        """Fetch all repairs and summary for dataset."""
        dataset = get_dataset_record(db, dataset_id)
        records = (
            db.query(RepairRecord)
            .filter(RepairRecord.dataset_id == dataset_id)
            .order_by(RepairRecord.repair_id.asc())
            .all()
        )

        summary = RepairSummary(
            total=len(records),
            pending=sum(1 for r in records if r.status == "pending"),
            approved=sum(1 for r in records if r.status == "approved"),
            rejected=sum(1 for r in records if r.status == "rejected"),
            applied=sum(1 for r in records if r.status == "applied"),
            failed=sum(1 for r in records if r.status == "failed"),
        )

        has_repaired = bool(dataset.repaired_file_path and os.path.exists(dataset.repaired_file_path))

        return RepairListResponse(
            dataset_id=dataset_id,
            summary=summary,
            has_repaired_dataset=has_repaired,
            repaired_file_path=dataset.repaired_file_path,
            repaired_at=dataset.repaired_at,
            repairs=[RepairResponse.model_validate(r) for r in records],
        )

    @classmethod
    def approve_repair(cls, db: Session, dataset_id: str, repair_id: str) -> RepairResponse:
        """Mark a repair proposal as approved."""
        repair = (
            db.query(RepairRecord)
            .filter(RepairRecord.dataset_id == dataset_id, RepairRecord.repair_id == repair_id)
            .first()
        )
        if not repair:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repair proposal '{repair_id}' not found for dataset '{dataset_id}'.",
            )

        if repair.status == "applied":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Repair '{repair_id}' has already been applied.",
            )

        if not repair.proposed_value or repair.proposed_value.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Repair '{repair_id}' requires a proposed value before approval. Please edit the proposed value first.",
            )

        repair.status = "approved"
        repair.error_message = None
        db.commit()
        db.refresh(repair)
        return RepairResponse.model_validate(repair)

    @classmethod
    def reject_repair(cls, db: Session, dataset_id: str, repair_id: str) -> RepairResponse:
        """Mark a repair proposal as rejected."""
        repair = (
            db.query(RepairRecord)
            .filter(RepairRecord.dataset_id == dataset_id, RepairRecord.repair_id == repair_id)
            .first()
        )
        if not repair:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repair proposal '{repair_id}' not found for dataset '{dataset_id}'.",
            )

        if repair.status == "applied":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject repair '{repair_id}': it has already been applied.",
            )

        repair.status = "rejected"
        db.commit()
        db.refresh(repair)
        return RepairResponse.model_validate(repair)

    @classmethod
    def update_repair(
        cls, db: Session, dataset_id: str, repair_id: str, proposed_value: Optional[str]
    ) -> RepairResponse:
        """Edit the proposed value of a repair before approval."""
        repair = (
            db.query(RepairRecord)
            .filter(RepairRecord.dataset_id == dataset_id, RepairRecord.repair_id == repair_id)
            .first()
        )
        if not repair:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repair proposal '{repair_id}' not found for dataset '{dataset_id}'.",
            )

        if repair.status == "applied":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit repair '{repair_id}': it has already been applied.",
            )

        val = proposed_value.strip() if (proposed_value is not None) else None
        repair.proposed_value = val

        # If user cleared the value, it cannot remain approved
        if not val and repair.status == "approved":
            repair.status = "pending"

        db.commit()
        db.refresh(repair)
        return RepairResponse.model_validate(repair)

    @classmethod
    def apply_approved_repairs(cls, db: Session, dataset_id: str) -> RepairApplyResponse:
        """
        Safely execute ONLY user-approved repairs onto a separate working copy.
        The original uploaded file is NEVER modified or overwritten.
        """
        record = get_dataset_record(db, dataset_id)

        # 1. Fetch all approved repairs
        approved_repairs = (
            db.query(RepairRecord)
            .filter(
                RepairRecord.dataset_id == dataset_id,
                RepairRecord.status == "approved",
            )
            .order_by(RepairRecord.row_index.asc())
            .all()
        )

        if not approved_repairs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No approved repairs found to apply. Please approve at least one repair first.",
            )

        # 2. Determine base working copy or original file
        # If a repaired file already exists on disk, continue from it
        if record.repaired_file_path and os.path.exists(record.repaired_file_path):
            base_file_path = record.repaired_file_path
        else:
            base_file_path = record.file_path

        df = load_dataframe_from_file(base_file_path, record.file_type)

        results: List[RepairResultItem] = []
        applied_count = 0
        failed_count = 0

        # Separate cell modifications from whole-row deletions
        cell_repairs: List[RepairRecord] = []
        row_repairs: List[RepairRecord] = []

        for r in approved_repairs:
            if r.repair_type == "deduplication" or r.column_name is None:
                row_repairs.append(r)
            else:
                cell_repairs.append(r)

        # 3. Apply cell modifications first
        for repair in cell_repairs:
            r_idx = repair.row_index
            col = repair.column_name

            # Boundary checks
            if r_idx < 0 or r_idx >= len(df):
                failed_count += 1
                msg = f"Row index {r_idx} is out of dataset bounds (total rows: {len(df)})."
                repair.status = "failed"
                repair.error_message = msg
                results.append(RepairResultItem(
                    repair_id=repair.repair_id,
                    status="failed",
                    message=msg,
                    column_name=col,
                    row_index=r_idx,
                ))
                continue

            if col not in df.columns:
                failed_count += 1
                msg = f"Column '{col}' does not exist in dataset."
                repair.status = "failed"
                repair.error_message = msg
                results.append(RepairResultItem(
                    repair_id=repair.repair_id,
                    status="failed",
                    message=msg,
                    column_name=col,
                    row_index=r_idx,
                ))
                continue

            # Stale value check
            curr_val = clean_cell_str(df.at[r_idx, col])
            exp_val = clean_cell_str(repair.original_value)
            if curr_val != exp_val:
                failed_count += 1
                msg = f"Stale value: cell currently contains '{curr_val}', but expected '{exp_val}'. Modification aborted for safety."
                repair.status = "failed"
                repair.error_message = msg
                results.append(RepairResultItem(
                    repair_id=repair.repair_id,
                    status="failed",
                    message=msg,
                    column_name=col,
                    row_index=r_idx,
                    before=curr_val,
                ))
                continue

            # Validate proposed value against column data type
            proposed = repair.proposed_value
            if proposed is None:
                failed_count += 1
                msg = "Proposed value is null/empty. Repair cannot be applied."
                repair.status = "failed"
                repair.error_message = msg
                results.append(RepairResultItem(
                    repair_id=repair.repair_id,
                    status="failed",
                    message=msg,
                    column_name=col,
                    row_index=r_idx,
                ))
                continue

            # Cast proposed value safely
            target_val = proposed
            col_series = df[col]
            if pd.api.types.is_numeric_dtype(col_series):
                try:
                    target_val = float(proposed)
                    if detect_column_type(col_series) == "integer" and target_val.is_integer():
                        target_val = int(target_val)
                except ValueError:
                    failed_count += 1
                    msg = f"Validation failed: '{proposed}' cannot be converted to numeric for column '{col}'."
                    repair.status = "failed"
                    repair.error_message = msg
                    results.append(RepairResultItem(
                        repair_id=repair.repair_id,
                        status="failed",
                        message=msg,
                        column_name=col,
                        row_index=r_idx,
                    ))
                    continue

            # Apply change to DataFrame
            df.at[r_idx, col] = target_val
            repair.status = "applied"
            repair.applied_value = str(target_val)
            repair.applied_at = datetime.now(timezone.utc)
            applied_count += 1

            results.append(RepairResultItem(
                repair_id=repair.repair_id,
                status="applied",
                message=f"Successfully applied repair to column '{col}'.",
                column_name=col,
                row_index=r_idx,
                before=curr_val or "<null>",
                after=str(target_val),
            ))

        # 4. Apply deduplication (row drops) in descending order to avoid shifting indices
        rows_to_drop = []
        for repair in sorted(row_repairs, key=lambda x: x.row_index, reverse=True):
            r_idx = repair.row_index
            if r_idx < 0 or r_idx >= len(df):
                failed_count += 1
                msg = f"Cannot remove duplicate row: index {r_idx} out of bounds."
                repair.status = "failed"
                repair.error_message = msg
                results.append(RepairResultItem(
                    repair_id=repair.repair_id,
                    status="failed",
                    message=msg,
                    row_index=r_idx,
                ))
                continue

            rows_to_drop.append(r_idx)
            repair.status = "applied"
            repair.applied_value = "[REMOVED_ROW]"
            repair.applied_at = datetime.now(timezone.utc)
            applied_count += 1

            results.append(RepairResultItem(
                repair_id=repair.repair_id,
                status="applied",
                message=f"Removed duplicate row at index {r_idx}.",
                row_index=r_idx,
                before="Duplicate row",
                after="[REMOVED]",
            ))

        if rows_to_drop:
            df = df.drop(index=rows_to_drop).reset_index(drop=True)

        # 5. Save working copy to disk if any repairs applied
        ext = "csv" if record.file_type == "csv" else "xlsx"
        repaired_filename = f"{dataset_id}_repaired.{ext}"
        repaired_path = os.path.join(settings.UPLOAD_DIR, repaired_filename)

        if record.file_type == "csv":
            df.to_csv(repaired_path, index=False, encoding="utf-8")
        else:
            df.to_excel(repaired_path, index=False, engine="openpyxl")

        record.repaired_file_path = repaired_path
        record.repaired_at = datetime.now(timezone.utc)
        db.commit()

        return RepairApplyResponse(
            dataset_id=dataset_id,
            applied_count=applied_count,
            failed_count=failed_count,
            repaired_file_path=repaired_path,
            repaired_at=record.repaired_at,
            results=results,
        )
