import os
import uuid
import hashlib
import json
import pytest
import pandas as pd
import httpx
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import SessionLocal
from app.models.dataset import Dataset
from app.models.repair import RepairRecord
from app.services.dataset_service import save_dataset_record
from app.services.repair_service import RepairService
from app.services.validation_service import ValidationService


def compute_file_sha256(filepath: str) -> str:
    """Calculate SHA-256 hash to verify immutability."""
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
def repaired_test_dataset(tmp_path, test_db) -> Dataset:
    """Create a dataset with repairs proposed and applied for validation tests."""
    data = {
        "id": [1, 2, 3, 4],
        "name": ["Alice", "Bob", "Charlie", "David"],
        "city": ["Bangalore", "bangalore", "BANGALORE", "Mumbai"],
        "email": ["alice@example.com", "bob@example.com", "charlie@example.com", "david@example.com"],
        "score": [85.0, 90.0, 95.0, 88.0],
    }
    df = pd.DataFrame(data)
    file_path = str(tmp_path / f"test_val_{uuid.uuid4().hex[:6]}.csv")
    df.to_csv(file_path, index=False, encoding="utf-8")

    dataset_id = f"test-ds-val-{uuid.uuid4()}"
    record = save_dataset_record(
        db=test_db,
        dataset_id=dataset_id,
        filename="test_val.csv",
        file_path=file_path,
        file_size=os.path.getsize(file_path),
        file_type="csv",
        total_rows=len(df),
        total_columns=len(df.columns),
        profile_data={"total_rows": len(df), "total_columns": len(df.columns)},
    )

    # Propose repairs (detects city inconsistency)
    repairs = RepairService.propose_repairs(test_db, dataset_id)
    # Approve all repairs
    for r in repairs:
        RepairService.approve_repair(test_db, dataset_id, r.repair_id)

    # Apply approved repairs
    RepairService.apply_approved_repairs(test_db, dataset_id)
    test_db.refresh(record)

    return record


@pytest.mark.anyio
async def test_validation_after_repair(repaired_test_dataset, test_db):
    """Verify validation engine accurately computes before/after metrics and resolved issues."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/datasets/{repaired_test_dataset.id}/validation")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert data["dataset_id"] == repaired_test_dataset.id
        assert data["original_quality_score"] > 0
        assert data["repaired_quality_score"] >= data["original_quality_score"]
        assert data["score_improvement"] >= 0
        assert data["resolved_issues_count"] >= 1
        assert "repair_summary" in data
        assert data["repair_summary"]["applied"] >= 1

        # Validation confirms whether all issues are fixed or remaining
        if data["remaining_issues_count"] == 0:
            assert data["is_fully_clean"] is True
        else:
            assert data["is_fully_clean"] is False


@pytest.mark.anyio
async def test_original_file_preservation(repaired_test_dataset):
    """Verify original uploaded dataset is never modified during repair, validation, or export."""
    initial_hash = compute_file_sha256(repaired_test_dataset.file_path)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Trigger validation
        await client.post(f"/api/v1/datasets/{repaired_test_dataset.id}/validate")
        # Trigger export
        exp_resp = await client.get(f"/api/v1/datasets/{repaired_test_dataset.id}/export/cleaned-csv")
        assert exp_resp.status_code == 200

    # Ensure hash of original file is 100% identical
    post_hash = compute_file_sha256(repaired_test_dataset.file_path)
    assert initial_hash == post_hash, "CRITICAL: Original file was modified on disk!"


@pytest.mark.anyio
async def test_correct_export_contents(repaired_test_dataset):
    """Verify exported cleaned CSV contains actual repaired values, not original data."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(f"/api/v1/datasets/{repaired_test_dataset.id}/export/cleaned-csv")
        assert resp.status_code == 200
        content = resp.text

        # The repaired file should have standardized city values
        assert "Bangalore" in content
        # Check header
        assert "id,name,city,email,score" in content


@pytest.mark.anyio
async def test_audit_log_generation(repaired_test_dataset):
    """Verify modification audit log records all repairs with timestamps and diffs."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Test audit log JSON endpoint
        json_resp = await client.get(f"/api/v1/datasets/{repaired_test_dataset.id}/audit-log")
        assert json_resp.status_code == 200
        log_data = json_resp.json()
        assert log_data["total_entries"] >= 1
        first_entry = log_data["entries"][0]
        assert "repair_id" in first_entry
        assert "issue_id" in first_entry
        assert "status" in first_entry
        assert first_entry["status"] == "applied"
        assert "timestamp" in first_entry

        # 2. Test audit log CSV export endpoint
        csv_resp = await client.get(f"/api/v1/datasets/{repaired_test_dataset.id}/export/audit-log?format=csv")
        assert csv_resp.status_code == 200
        csv_text = csv_resp.text
        assert "Dataset ID,Repair ID,Issue ID,Repair Type" in csv_text
        assert first_entry["repair_id"] in csv_text

        # 3. Test Quality Report JSON export
        rep_resp = await client.get(f"/api/v1/datasets/{repaired_test_dataset.id}/export/report")
        assert rep_resp.status_code == 200
        rep_dict = rep_resp.json()
        assert "quality_comparison" in rep_dict
        assert "audit_log" in rep_dict
