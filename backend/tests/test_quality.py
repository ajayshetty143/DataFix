import pytest
import pandas as pd
import httpx

from app.main import app
from app.services.detection.missing_detector import detect_missing_values
from app.services.detection.duplicate_detector import detect_duplicates
from app.services.detection.format_detector import detect_invalid_formats
from app.services.detection.inconsistency_detector import detect_inconsistencies
from app.services.detection.anomaly_detector import detect_statistical_anomalies
from app.services.detection.engine import QualityDetectionEngine

MESSY_CSV_PATH = "E:\\Hackathon\\DataFix\\backend\\tests\\messy_dataset.csv"


@pytest.fixture
def messy_df():
    return pd.read_csv(MESSY_CSV_PATH)


def test_missing_detector(messy_df):
    issues = detect_missing_values(messy_df)
    assert len(issues) >= 2  # At least email and status have missing/empty/whitespace/placeholders

    email_issue = next(i for i in issues if i.column == "email")
    assert email_issue.affected_count >= 2  # Row 7 (null) and Row 15 (whitespace)
    assert email_issue.category == "missing_value"

    status_issue = next(i for i in issues if i.column == "status")
    assert status_issue.affected_count >= 2  # Row 11 (whitespace) and Row 15 ("N/A")
    assert status_issue.metadata["whitespace_count"] >= 1
    assert status_issue.metadata["placeholder_count"] >= 1


def test_duplicate_detector(messy_df):
    issues = detect_duplicates(messy_df)
    exact_issue = next((i for i in issues if "Exact Duplicate" in i.title), None)
    assert exact_issue is not None
    assert exact_issue.category == "duplicate"
    assert exact_issue.affected_count == 2
    # Rows 3 and 10 are exact duplicates of each other
    assert 3 in exact_issue.row_indices
    assert 10 in exact_issue.row_indices

    # Check near duplicates (Row 5 & Row 12 differ only in casing/spaces)
    near_issue = next((i for i in issues if "Near-Duplicate" in i.title), None)
    if near_issue:
        assert 5 in near_issue.row_indices
        assert 12 in near_issue.row_indices


def test_format_detector_and_false_positives(messy_df):
    issues = detect_invalid_formats(messy_df)

    # Verify invalid emails detected
    email_issue = next((i for i in issues if i.column == "email"), None)
    assert email_issue is not None
    assert email_issue.category == "invalid_format"
    assert email_issue.severity == "critical"
    # Row 4 (diana@@), Row 6 (fiona@chicago), Row 13 (missing_at_symbol.com)
    assert 4 in email_issue.row_indices
    assert 6 in email_issue.row_indices
    assert 13 in email_issue.row_indices

    # Verify invalid dates detected
    date_issue = next((i for i in issues if i.column == "signup_date"), None)
    assert date_issue is not None
    assert date_issue.category == "invalid_format"
    # Row 6 (2023-13-45) and Row 8 (not_a_date)
    assert 6 in date_issue.row_indices
    assert 8 in date_issue.row_indices

    # CRITICAL: Verify FALSE POSITIVES avoided for normal string columns like 'notes'
    notes_issue = next((i for i in issues if i.column == "notes"), None)
    assert notes_issue is None, "Normal text column 'notes' should NOT be falsely flagged as invalid email or date!"


def test_inconsistency_detector(messy_df):
    issues = detect_inconsistencies(messy_df)
    city_issue = next((i for i in issues if i.column == "city"), None)
    assert city_issue is not None
    assert city_issue.category == "inconsistency"
    assert city_issue.suggested_action is not None

    # Check clusters inside metadata
    clusters = city_issue.metadata["clusters"]
    norm_keys = [c["normalized_key"] for c in clusters]
    assert "bangalore" in norm_keys
    assert "new york" in norm_keys

    # Verify status column has casing inconsistencies (Active, active, ACTIVE)
    status_issue = next((i for i in issues if i.column == "status"), None)
    assert status_issue is not None
    assert status_issue.metadata["cluster_count"] >= 1


def test_statistical_anomaly_detector_and_constant_columns(messy_df):
    issues = detect_statistical_anomalies(messy_df)

    salary_issue = next((i for i in issues if i.column == "salary"), None)
    assert salary_issue is not None
    assert salary_issue.category == "statistical_anomaly"
    # Row 11 (15000000) and Row 15 (-99999) must be flagged
    assert 11 in salary_issue.row_indices
    assert 15 in salary_issue.row_indices
    assert salary_issue.metadata["extreme_count"] >= 1

    # CRITICAL: Verify constant column 'company' was safely handled without crash or division by zero
    company_issue = next((i for i in issues if i.column == "company"), None)
    assert company_issue is None, "Constant column with std=0 should safely skip outlier detection!"


def test_empty_dataset_safety():
    empty_df = pd.DataFrame(columns=["a", "b", "c"])
    # All detectors must safely return empty list without throwing exceptions
    assert detect_missing_values(empty_df) == []
    assert detect_duplicates(empty_df) == []
    assert detect_invalid_formats(empty_df) == []
    assert detect_inconsistencies(empty_df) == []
    assert detect_statistical_anomalies(empty_df) == []

    engine_res = QualityDetectionEngine.analyze(empty_df, "test-empty", "empty.csv")
    assert engine_res["summary"]["total_issues"] == 0
    assert engine_res["summary"]["quality_score"] == 100.0


@pytest.mark.anyio
async def test_quality_analysis_api_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with open(MESSY_CSV_PATH, "rb") as f:
            files = {"file": ("messy_dataset.csv", f, "text/csv")}
            up_resp = await client.post("/api/v1/datasets/upload", files=files)

        assert up_resp.status_code == 201
        dataset_id = up_resp.json()["id"]

        # Call GET /api/v1/datasets/{dataset_id}/quality
        resp = await client.get(f"/api/v1/datasets/{dataset_id}/quality")
        assert resp.status_code == 200
        data = resp.json()

        assert data["dataset_id"] == dataset_id
        summary = data["summary"]
        assert summary["total_issues"] >= 5
        assert summary["total_affected_rows"] > 0
        assert summary["total_affected_columns"] > 0
        assert 0.0 <= summary["quality_score"] <= 100.0

        # Verify all 5 categories are present in by_category
        cats = summary["by_category"]
        assert "missing_value" in cats and cats["missing_value"] >= 1
        assert "duplicate" in cats and cats["duplicate"] >= 1
        assert "invalid_format" in cats and cats["invalid_format"] >= 1
        assert "inconsistency" in cats and cats["inconsistency"] >= 1
        assert "statistical_anomaly" in cats and cats["statistical_anomaly"] >= 1

        # Check issue structure
        first_issue = summary["issues"][0]
        assert "id" in first_issue
        assert "category" in first_issue
        assert "severity" in first_issue
        assert "row_indices" in first_issue

        # Test POST /api/v1/datasets/{dataset_id}/analyze trigger
        re_resp = await client.post(f"/api/v1/datasets/{dataset_id}/analyze")
        assert re_resp.status_code == 200
        assert re_resp.json()["summary"]["total_issues"] == summary["total_issues"]
