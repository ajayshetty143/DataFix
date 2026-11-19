import hashlib
import json
import os
import pytest
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.dataset import Base, Dataset
from app.models.repair import RepairRecord
from app.services.detection.anomaly_detector import detect_statistical_anomalies
from app.services.detection.engine import QualityDetectionEngine
from app.services.repair_service import RepairService
from app.services.validation_service import ValidationService
from fastapi import HTTPException


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def calculate_sha256(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


# =============================================================================
# 1. HEALTHCARE AUDIT: PATIENT AGE DOMAIN VALIDATION
# =============================================================================

def test_negative_and_extreme_patient_age_detection():
    """
    Healthcare dataset test:
    - patient_age = -4 (biologically invalid domain value)
    - patient_age = 250 (exceeds human lifespan and extreme statistical outlier)
    - Regular ages: 25, 34, 45, 52, 60, 31, 29, 41
    Verify:
    1. Both -4 and 250 are identified as anomalies.
    2. Does not rely solely on IQR/Z-score to catch -4.
    3. Both are flagged with explicit domain reasons and marked extreme.
    """
    df = pd.DataFrame({
        "patient_id": [f"PID-{i:03d}" for i in range(1, 11)],
        "patient_age": [25, 34, 45, -4, 52, 60, 31, 250, 29, 41],
        "department": ["Cardiology"] * 10
    })

    issues = detect_statistical_anomalies(df)
    age_issues = [i for i in issues if i.column == "patient_age"]

    assert len(age_issues) == 1
    issue = age_issues[0]
    assert issue.category == "statistical_anomaly"

    # Both -4 (row 4) and 250 (row 8) must be flagged
    assert 4 in issue.row_indices
    assert 8 in issue.row_indices
    assert issue.affected_count >= 2

    # Check anomaly metadata
    anomalies = issue.metadata["anomalies"]
    row4_anomaly = next(a for a in anomalies if a["row"] == 4)
    row8_anomaly = next(a for a in anomalies if a["row"] == 8)

    assert row4_anomaly["value"] == -4
    assert row4_anomaly["bound_violation"] == "negative_age"
    assert "biologically invalid" in row4_anomaly["reason"]
    assert row4_anomaly["is_extreme"] is True

    assert row8_anomaly["value"] == 250
    assert row8_anomaly["bound_violation"] in ["unrealistic_human_age", "above_upper"]
    assert row8_anomaly["is_extreme"] is True


def test_patient_age_repair_requires_manual_review(in_memory_db, tmp_path):
    """
    Verify repair engine behavior for patient_age = -4 and 250:
    - proposed_value MUST be None (no automatic capping or inventing values)
    - human_review_required MUST be True
    - Cannot approve without explicit user-provided replacement
    """
    csv_file = tmp_path / "healthcare_patients.csv"
    df = pd.DataFrame({
        "patient_id": [f"PID-{i:03d}" for i in range(1, 11)],
        "patient_age": [25, 34, 45, -4, 52, 60, 31, 250, 29, 41],
    })
    df.to_csv(csv_file, index=False)

    record = Dataset(
        id="ds_healthcare_001",
        filename="healthcare_patients.csv",
        file_path=str(csv_file),
        file_size=os.path.getsize(str(csv_file)),
        file_type="csv",
        total_rows=10,
        total_columns=2,
    )
    in_memory_db.add(record)
    in_memory_db.commit()

    # Generate repair proposals
    repairs = RepairService.propose_repairs(in_memory_db, "ds_healthcare_001")
    age_repairs = [r for r in repairs if r.column_name == "patient_age"]

    assert len(age_repairs) >= 2
    for r in age_repairs:
        assert r.proposed_value is None
        assert r.human_review_required is True
        assert r.status == "pending"
        assert r.confidence == "Low"

    # Verify that approving directly without proposed value raises HTTPException (400)
    first_rep = age_repairs[0]
    with pytest.raises(HTTPException) as exc_info:
        RepairService.approve_repair(in_memory_db, "ds_healthcare_001", first_rep.repair_id)
    assert exc_info.value.status_code == 400
    assert "requires a proposed value before approval" in exc_info.value.detail


# =============================================================================
# 2. HEALTHCARE AUDIT: CONSULTATION FEE VALIDATION
# =============================================================================

def test_negative_and_extreme_consultation_fee_detection():
    """
    Healthcare dataset test:
    - consultation_fee = -500 (negative fee without refund/credit semantics)
    - consultation_fee = 999999 (extreme anomaly/outlier)
    - Regular fees: 150, 200, 175, 220, 180, 250, 160, 190
    Verify:
    1. consultation_fee = -500 flagged without refund semantics.
    2. consultation_fee = 999999 flagged as extreme outlier.
    3. Normal credit/refund column names (e.g. refund_amount) are NOT wrongly flagged for negative values.
    """
    df = pd.DataFrame({
        "patient_id": [f"PID-{i:03d}" for i in range(1, 11)],
        "consultation_fee": [150, 200, 175, -500, 220, 180, 250, 999999, 160, 190],
        "refund_fee": [0, -50, 0, -100, 0, 0, -20, 0, 0, 0]  # explicit refund semantics
    })

    issues = detect_statistical_anomalies(df)

    fee_issues = [i for i in issues if i.column == "consultation_fee"]
    assert len(fee_issues) == 1
    issue = fee_issues[0]

    # Row 4 (-500) and Row 8 (999999) must be flagged
    assert 4 in issue.row_indices
    assert 8 in issue.row_indices

    anomalies = issue.metadata["anomalies"]
    row4 = next(a for a in anomalies if a["row"] == 4)
    assert row4["value"] == -500
    assert "refund/credit semantics" in row4["reason"]

    # Explicit refund column should NOT be flagged with negative_fee_without_refund_semantics
    refund_issues = [i for i in issues if i.column == "refund_fee"]
    if refund_issues:
        for a in refund_issues[0].metadata.get("anomalies", []):
            assert a.get("bound_violation") != "negative_fee_without_refund_semantics"


def test_consultation_fee_no_automatic_change_or_delete(in_memory_db, tmp_path):
    """
    Verify that negative consultation fee and extreme values are never
    automatically modified or deleted.
    """
    csv_file = tmp_path / "consultation_fees.csv"
    df = pd.DataFrame({
        "doctor": ["Dr. Smith"] * 10,
        "consultation_fee": [150, 200, 175, -500, 220, 180, 250, 999999, 160, 190],
    })
    df.to_csv(csv_file, index=False)

    record = Dataset(
        id="ds_fee_001",
        filename="consultation_fees.csv",
        file_path=str(csv_file),
        file_size=os.path.getsize(str(csv_file)),
        file_type="csv",
        total_rows=10,
        total_columns=2,
    )
    in_memory_db.add(record)
    in_memory_db.commit()

    repairs = RepairService.propose_repairs(in_memory_db, "ds_fee_001")
    fee_repairs = [r for r in repairs if r.column_name == "consultation_fee"]

    assert len(fee_repairs) >= 2
    for r in fee_repairs:
        # Proposed value must be None
        assert r.proposed_value is None
        assert r.human_review_required is True


# =============================================================================
# 3. VALIDATION, AUDIT CONSISTENCY & ISSUE ID PRESERVATION
# =============================================================================

def test_validation_and_audit_issue_id_consistency(in_memory_db, tmp_path):
    """
    Verify:
    1. Issue IDs regenerated after revalidation do NOT corrupt the original repair-to-issue relationship.
    2. Original issue IDs are preserved in RepairRecord.issue_id.
    3. Resolved and remaining issue counts are accurate.
    4. Applied repair records match actual working-copy modifications.
    """
    csv_file = tmp_path / "healthcare_audit.csv"
    df = pd.DataFrame({
        "patient_id": [f"PID-{i:03d}" for i in range(1, 11)],
        "patient_age": [25, 34, 45, -4, 52, 60, 31, 250, 29, 41],
        "city": ["Mumbai", "mumbai", "Mumbai", "Mumbai", "Pune", "Pune", "Pune", "Pune", "Pune", "Pune"],
    })
    df.to_csv(csv_file, index=False)

    record = Dataset(
        id="ds_audit_test_001",
        filename="healthcare_audit.csv",
        file_path=str(csv_file),
        file_size=os.path.getsize(str(csv_file)),
        file_type="csv",
        total_rows=10,
        total_columns=3,
    )
    in_memory_db.add(record)
    in_memory_db.commit()

    # Step 1: Baseline detection & proposal
    repairs = RepairService.propose_repairs(in_memory_db, "ds_audit_test_001")
    assert len(repairs) > 0

    # Store baseline issue IDs for each repair
    original_repair_issue_map = {r.repair_id: r.issue_id for r in repairs}

    # Step 2: Approve only the city inconsistency repair
    city_repairs = [r for r in repairs if r.column_name == "city"]
    assert len(city_repairs) == 1
    target_city_rep = city_repairs[0]
    RepairService.approve_repair(in_memory_db, "ds_audit_test_001", target_city_rep.repair_id)

    # Step 3: Apply approved repairs
    apply_res = RepairService.apply_approved_repairs(in_memory_db, "ds_audit_test_001")
    assert apply_res.applied_count == 1
    assert apply_res.failed_count == 0

    # Check working copy modified cell matches applied repair record
    df_repaired = pd.read_csv(record.repaired_file_path)
    assert df_repaired.at[target_city_rep.row_index, "city"] == target_city_rep.proposed_value

    # Step 4: Validate repairs
    val_report = ValidationService.validate_repairs(in_memory_db, "ds_audit_test_001", force_recompute=True)

    # Verify issue ID relationship was not corrupted in database
    db_repairs = in_memory_db.query(RepairRecord).filter(RepairRecord.dataset_id == "ds_audit_test_001").all()
    for r in db_repairs:
        assert r.issue_id == original_repair_issue_map[r.repair_id]

    # Verify audit log entries preserve original issue IDs
    audit_log = ValidationService.get_audit_log(in_memory_db, "ds_audit_test_001")
    applied_log = next(e for e in audit_log if e["repair_id"] == target_city_rep.repair_id)
    assert applied_log["issue_id"] == target_city_rep.issue_id
    assert applied_log["status"] == "applied"
    assert applied_log["new_value"] == "Mumbai"

    # Verify resolved issues list contains the resolved city issue
    resolved = val_report["resolved_issues"]
    assert len(resolved) == 1
    assert resolved[0]["column"] == "city"
    assert resolved[0]["issue_id"] == target_city_rep.issue_id

    # Verify remaining issues still report the age anomaly with preserved original_issue_id
    remaining = val_report["remaining_issues"]
    age_remaining = next(i for i in remaining if i.get("column") == "patient_age")
    assert age_remaining is not None
    assert "original_issue_id" in age_remaining

    # Confirm is_fully_clean is False since age anomaly is still unresolved
    assert val_report["is_fully_clean"] is False
    assert val_report["remaining_issues_count"] > 0


# =============================================================================
# 4. ORIGINAL FILE IMMUTABILITY & EXPORT INTEGRITY
# =============================================================================

def test_original_file_immutability_and_export_integrity(in_memory_db, tmp_path):
    """
    Verify:
    1. Original uploaded file hash is identical before and after repair operations.
    2. Repaired file is strictly saved to separate working path.
    3. Export contains approved repairs while original file remains untouched.
    """
    csv_file = tmp_path / "original_records.csv"
    initial_content = (
        "id,status,score\n"
        "1,active,90\n"
        "2,Active,85\n"
        "3,active,95\n"
        "4,active,88\n"
    )
    csv_file.write_text(initial_content, encoding="utf-8")
    initial_hash = calculate_sha256(str(csv_file))

    record = Dataset(
        id="ds_immutable_001",
        filename="original_records.csv",
        file_path=str(csv_file),
        file_size=os.path.getsize(str(csv_file)),
        file_type="csv",
        total_rows=4,
        total_columns=3,
    )
    in_memory_db.add(record)
    in_memory_db.commit()

    # Propose repairs
    repairs = RepairService.propose_repairs(in_memory_db, "ds_immutable_001")
    assert len(repairs) >= 1

    # Approve and apply the status repair
    status_rep = next(r for r in repairs if r.column_name == "status")
    RepairService.approve_repair(in_memory_db, "ds_immutable_001", status_rep.repair_id)
    RepairService.apply_approved_repairs(in_memory_db, "ds_immutable_001")

    # Verify original file hash has NOT changed at all
    post_repair_hash = calculate_sha256(str(csv_file))
    assert post_repair_hash == initial_hash, "CRITICAL: Original file was modified during repair application!"

    # Export cleaned dataset
    cleaned_path, cleaned_filename = ValidationService.get_cleaned_csv_path(in_memory_db, "ds_immutable_001")
    assert os.path.exists(cleaned_path)
    assert cleaned_path != str(csv_file)

    # Post-export hash check on original file
    post_export_hash = calculate_sha256(str(csv_file))
    assert post_export_hash == initial_hash, "CRITICAL: Original file was modified during export generation!"

    # Cleaned file contains the repair
    cleaned_df = pd.read_csv(cleaned_path)
    assert cleaned_df.at[1, "status"] == "active"

    # Original file still contains the dirty data
    orig_df = pd.read_csv(str(csv_file))
    assert orig_df.at[1, "status"] == "Active"
