import os
import uuid
import hashlib
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
import httpx
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models.dataset import Dataset
from app.models.repair import RepairRecord
from app.services.dataset_service import save_dataset_record
from app.services.repair_service import RepairService


def calculate_file_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a file to verify immutability."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


@pytest.fixture
def test_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def messy_test_dataset(tmp_path, test_db) -> Dataset:
    """Create a temporary test dataset with controlled quality issues."""
    data = {
        "id": [1, 2, 3, 4, 5, 2],  # Duplicate row 5 is duplicate of row 1 (0-indexed)
        "name": ["Alice", "Bob", "Charlie", "David", "Eve", "Bob"],
        "age": [25, None, 35, 25, 100, None],  # Missing values at row 1 & 5, outlier at row 4
        "city": ["Bangalore", "bangalore", "BANGALORE", "Mumbai", "mumbai", "bangalore"],
        "email": ["alice@example.com", "not-an-email", "charlie@example.com", "david@example.com", "eve@example.com", "not-an-email"],
        "score": [10.0, 20.0, 30.0, 9999.0, 15.0, 20.0],  # Outlier 9999.0 at row 3
    }
    df = pd.DataFrame(data)
    file_path = str(tmp_path / f"test_repairs_messy_{uuid.uuid4().hex[:6]}.csv")
    df.to_csv(file_path, index=False, encoding="utf-8")

    record = save_dataset_record(
        db=test_db,
        dataset_id=f"test-ds-{uuid.uuid4()}",
        filename="test_repairs_messy.csv",
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        file_type="csv",
        total_rows=len(df),
        total_columns=len(df.columns),
        profile_data={"columns": list(df.columns)},
    )
    return record


def test_propose_repairs_categories(test_db, messy_test_dataset):
    """Verify repair proposals for all 5 categories."""
    proposals = RepairService.propose_repairs(test_db, messy_test_dataset.id)
    assert len(proposals) > 0

    types = {r.repair_type for r in proposals}
    assert "missing_imputation" in types
    assert "deduplication" in types
    assert "category_normalization" in types

    # 1. Check numeric missing value has median proposed
    age_repairs = [r for r in proposals if r.column_name == "age" and r.repair_type == "missing_imputation"]
    assert len(age_repairs) > 0
    for ar in age_repairs:
        assert ar.proposed_value is not None
        assert float(ar.proposed_value) in [25.0, 27.5, 30.0, 35.0]  # valid median
        assert ar.confidence == "High"
        assert ar.human_review_required is False

    # 2. Check duplicate repair proposes row drop
    dup_repairs = [r for r in proposals if r.repair_type == "deduplication"]
    assert len(dup_repairs) > 0
    for dr in dup_repairs:
        assert dr.proposed_value == "[REMOVE_DUPLICATE_ROW]"
        assert dr.confidence == "High"

    # 3. Check categorical normalization proposes canonical casing
    city_repairs = [r for r in proposals if r.column_name == "city" and r.repair_type == "category_normalization"]
    assert len(city_repairs) > 0
    for cr in city_repairs:
        assert cr.proposed_value.lower() in ["bangalore", "mumbai"]
        assert cr.confidence == "High"

    # 4. Check invalid format & anomaly require human review
    manual_repairs = [r for r in proposals if r.human_review_required is True]
    assert len(manual_repairs) > 0


def test_approve_and_reject_repairs(test_db, messy_test_dataset):
    """Verify approval and rejection mechanics."""
    proposals = RepairService.propose_repairs(test_db, messy_test_dataset.id)

    # Find a repair with a proposed value
    valid_repair = next(r for r in proposals if r.proposed_value)
    repair_id = valid_repair.repair_id

    # Approve
    approved = RepairService.approve_repair(test_db, messy_test_dataset.id, repair_id)
    assert approved.status == "approved"

    # Reject
    rejected = RepairService.reject_repair(test_db, messy_test_dataset.id, repair_id)
    assert rejected.status == "rejected"

    # Re-approve
    reapproved = RepairService.approve_repair(test_db, messy_test_dataset.id, repair_id)
    assert reapproved.status == "approved"


def test_prevent_approving_empty_proposed_value(test_db, messy_test_dataset):
    """Verify cannot approve a repair that requires manual review when proposed_value is None."""
    proposals = RepairService.propose_repairs(test_db, messy_test_dataset.id)
    manual_repair = next((r for r in proposals if not r.proposed_value), None)

    if manual_repair:
        with pytest.raises(HTTPException) as exc_info:
            RepairService.approve_repair(test_db, messy_test_dataset.id, manual_repair.repair_id)
        assert exc_info.value.status_code == 400
        assert "requires a proposed value" in exc_info.value.detail

        # Now edit it and then approve
        updated = RepairService.update_repair(test_db, messy_test_dataset.id, manual_repair.repair_id, "corrected_val")
        assert updated.proposed_value == "corrected_val"
        approved = RepairService.approve_repair(test_db, messy_test_dataset.id, manual_repair.repair_id)
        assert approved.status == "approved"


def test_apply_only_approved_repairs_and_preserve_original(test_db, messy_test_dataset):
    """Verify that ONLY approved repairs are applied and original file is NEVER modified."""
    initial_hash = calculate_file_hash(messy_test_dataset.file_path)

    proposals = RepairService.propose_repairs(test_db, messy_test_dataset.id)

    # Approve exactly ONE repair
    target_repair = next(r for r in proposals if r.repair_type == "category_normalization" and r.proposed_value)
    RepairService.approve_repair(test_db, messy_test_dataset.id, target_repair.repair_id)

    # Apply approved repairs
    apply_resp = RepairService.apply_approved_repairs(test_db, messy_test_dataset.id)
    assert apply_resp.applied_count == 1
    assert apply_resp.failed_count == 0
    assert os.path.exists(apply_resp.repaired_file_path)

    # CRITICAL: Verify original file hash has NOT changed!
    post_hash = calculate_file_hash(messy_test_dataset.file_path)
    assert initial_hash == post_hash, "Original dataset file was modified!"

    # Verify separate repaired file has the modification
    df_repaired = pd.read_csv(apply_resp.repaired_file_path)
    assert df_repaired.at[target_repair.row_index, target_repair.column_name] == target_repair.proposed_value


def test_prevent_duplicate_application(test_db, messy_test_dataset):
    """Verify applied repairs cannot be re-applied or rejected."""
    proposals = RepairService.propose_repairs(test_db, messy_test_dataset.id)
    target = next(r for r in proposals if r.proposed_value)
    RepairService.approve_repair(test_db, messy_test_dataset.id, target.repair_id)
    RepairService.apply_approved_repairs(test_db, messy_test_dataset.id)

    # Attempt to approve already applied repair
    with pytest.raises(HTTPException) as exc_info:
        RepairService.approve_repair(test_db, messy_test_dataset.id, target.repair_id)
    assert exc_info.value.status_code == 400
    assert "already been applied" in exc_info.value.detail

    # Attempt to reject already applied repair
    with pytest.raises(HTTPException) as exc_info2:
        RepairService.reject_repair(test_db, messy_test_dataset.id, target.repair_id)
    assert exc_info2.value.status_code == 400

    # Attempt to apply again when no approved repairs remain
    with pytest.raises(HTTPException) as exc_info3:
        RepairService.apply_approved_repairs(test_db, messy_test_dataset.id)
    assert exc_info3.value.status_code == 400


def test_detect_stale_value_failure(test_db, messy_test_dataset):
    """Verify that if the cell value in data has changed since proposal, application fails safely."""
    proposals = RepairService.propose_repairs(test_db, messy_test_dataset.id)
    target = next(r for r in proposals if r.column_name == "city" and r.proposed_value)

    # Approve repair
    RepairService.approve_repair(test_db, messy_test_dataset.id, target.repair_id)

    # Directly alter the original value in the repair record to simulate stale state
    rec = test_db.query(RepairRecord).filter(RepairRecord.id == target.id).first()
    rec.original_value = "NonExistentStaleValue"
    test_db.commit()

    # Attempt apply
    apply_resp = RepairService.apply_approved_repairs(test_db, messy_test_dataset.id)
    assert apply_resp.failed_count == 1
    assert apply_resp.applied_count == 0
    assert any("Stale value" in r.message for r in apply_resp.results)


def test_repair_validation_failure_handling(test_db, messy_test_dataset):
    """Verify invalid data type assignment (e.g. text into integer) is caught and handled safely."""
    proposals = RepairService.propose_repairs(test_db, messy_test_dataset.id)
    age_repair = next(r for r in proposals if r.column_name == "age")

    # Update with an invalid non-numeric string
    RepairService.update_repair(test_db, messy_test_dataset.id, age_repair.repair_id, "invalid_non_number")
    RepairService.approve_repair(test_db, messy_test_dataset.id, age_repair.repair_id)

    apply_resp = RepairService.apply_approved_repairs(test_db, messy_test_dataset.id)
    assert apply_resp.failed_count == 1
    assert any("Validation failed" in r.message for r in apply_resp.results)


@pytest.mark.anyio
async def test_repair_endpoints_integration(test_db):
    """Integration test for all Phase 5 repair API endpoints."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Upload a dataset
        csv_data = b"id,val,city\n1,10,Bangalore\n2,,bangalore\n3,30,BANGALORE\n"
        files = {"file": ("test_endpoints.csv", csv_data, "text/csv")}
        up_resp = await ac.post("/api/v1/datasets/upload", files=files)
        assert up_resp.status_code == 201
        dataset_id = up_resp.json()["id"]

        # 2. Get repair proposals
        get_repairs_resp = await ac.get(f"/api/v1/datasets/{dataset_id}/repairs")
        assert get_repairs_resp.status_code == 200
        repairs_data = get_repairs_resp.json()
        assert repairs_data["summary"]["total"] >= 1
        repairs = repairs_data["repairs"]
        repair_id = repairs[0]["repair_id"]

        # 3. Edit proposed value
        patch_resp = await ac.patch(
            f"/api/v1/datasets/{dataset_id}/repairs/{repair_id}",
            json={"proposed_value": "99"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["proposed_value"] == "99"

        # 4. Approve repair
        app_resp = await ac.post(f"/api/v1/datasets/{dataset_id}/repairs/{repair_id}/approve")
        assert app_resp.status_code == 200
        assert app_resp.json()["status"] == "approved"

        # 5. Apply approved repairs
        apply_resp = await ac.post(f"/api/v1/datasets/{dataset_id}/repairs/apply-approved")
        assert apply_resp.status_code == 200
        assert apply_resp.json()["applied_count"] >= 1

        # 6. Preview repaired dataset
        preview_resp = await ac.get(f"/api/v1/datasets/{dataset_id}/repairs/preview")
        assert preview_resp.status_code == 200
        assert len(preview_resp.json()["rows"]) == 3
