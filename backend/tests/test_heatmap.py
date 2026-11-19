import pytest
import pandas as pd
from app.services.detection.engine import QualityDetectionEngine
from app.services.detection.heatmap import generate_quality_heatmap


def test_heatmap_clean_dataset():
    """Verify clean dataset generates 100% healthy heatmap with proper N/A indications."""
    data = {
        "user_id": [101, 102, 103, 104, 105],
        "name": ["Alice", "Bob", "Charlie", "David", "Eve"],
        "email": ["alice@example.com", "bob@example.com", "charlie@example.com", "david@example.com", "eve@example.com"],
        "age": [25, 30, 35, 40, 45],
        "city": ["Bangalore", "Mumbai", "Delhi", "Chennai", "Kolkata"],
    }
    df = pd.DataFrame(data)
    res = QualityDetectionEngine.analyze(df, "test-clean", "clean.csv")
    summary = res["summary"]
    heatmap = summary.get("heatmap", [])

    assert len(heatmap) == len(df.columns)
    for col_item in heatmap:
        # Every column in clean dataset must be healthy
        assert col_item["overall_status"] == "healthy"
        assert col_item["total_issues_count"] == 0
        cells = col_item["cells"]

        # Missing values must be 0%
        assert cells["missing_value"]["percentage"] == 0.0
        assert cells["missing_value"]["severity"] == "healthy"

        # Duplicate involvement must be 0%
        assert cells["duplicate"]["percentage"] == 0.0
        assert cells["duplicate"]["severity"] == "healthy"

        # Numeric column checks
        if col_item["column_name"] == "age":
            # Continuous numeric measurement: anomaly is applicable and 0%
            assert cells["statistical_anomaly"]["is_applicable"] is True
            assert cells["statistical_anomaly"]["percentage"] == 0.0
            assert cells["inconsistency"]["is_applicable"] is False
        elif col_item["column_name"] == "user_id":
            # Numeric identifier: anomaly is excluded (N/A)
            assert cells["statistical_anomaly"]["is_applicable"] is False
            assert cells["statistical_anomaly"]["percentage"] is None
            assert cells["inconsistency"]["is_applicable"] is False
        else:
            # Text columns: anomaly is N/A
            assert cells["statistical_anomaly"]["is_applicable"] is False
            assert cells["statistical_anomaly"]["percentage"] is None


def test_heatmap_all_five_categories():
    """Verify heatmap accurately reflects all five issue categories without double-counting."""
    data = {
        "id": [1, 2, 3, 4, 5, 2],  # Duplicate row 5 is duplicate of row 1
        "user_name": ["Alice", "Bob", "Charlie", "David", "Eve", "Bob"],
        "email": ["alice@example.com", "invalid-email-no-at", "charlie@example.com", None, "eve@example.com", "invalid-email-no-at"],
        "city": ["Bangalore", "bangalore", "BANGALORE", "Mumbai", "mumbai", "bangalore"],
        "salary": [50000, 60000, 55000, 9999999, 52000, 60000],  # Outlier 9999999
    }
    df = pd.DataFrame(data)
    res = QualityDetectionEngine.analyze(df, "test-five", "all_five.csv")
    summary = res["summary"]
    heatmap = summary.get("heatmap", [])

    col_map = {item["column_name"]: item for item in heatmap}

    # 1. Email should have missing value AND invalid format
    email_cells = col_map["email"]["cells"]
    assert email_cells["missing_value"]["affected_count"] >= 1
    assert email_cells["invalid_format"]["affected_count"] >= 1

    # 2. City should have inconsistency
    city_cells = col_map["city"]["cells"]
    assert city_cells["inconsistency"]["affected_count"] >= 3
    assert city_cells["inconsistency"]["severity"] in ("moderate", "high")

    # 3. Salary should have statistical anomaly
    salary_cells = col_map["salary"]["cells"]
    assert salary_cells["statistical_anomaly"]["affected_count"] >= 1
    assert salary_cells["statistical_anomaly"]["severity"] in ("low", "moderate", "high")

    # 4. Duplicate involvement should be flagged
    assert col_map["user_name"]["cells"]["duplicate"]["affected_count"] >= 2


def test_heatmap_arbitrary_column_names():
    """Verify heatmap functions correctly with arbitrary, non-standard column names."""
    data = {
        "alpha_beta_123": ["val1", "val2", None],
        "delta_epsilon": [10.5, 20.2, 30.8],
        "zeta_omega_code": ["CODE-A", "code-a", "CODE-A"],
    }
    df = pd.DataFrame(data)
    res = QualityDetectionEngine.analyze(df, "test-arbitrary", "arbitrary.csv")
    heatmap = res["summary"].get("heatmap", [])

    col_names = [item["column_name"] for item in heatmap]
    assert col_names == ["alpha_beta_123", "delta_epsilon", "zeta_omega_code"]

    col_map = {item["column_name"]: item for item in heatmap}
    assert col_map["alpha_beta_123"]["cells"]["missing_value"]["affected_count"] == 1
    assert col_map["delta_epsilon"]["cells"]["missing_value"]["affected_count"] == 0
    assert col_map["zeta_omega_code"]["cells"]["inconsistency"]["affected_count"] == 1


def test_heatmap_empty_column():
    """Verify empty column is flagged with 100% missing values and high severity."""
    data = {
        "id": [1, 2, 3],
        "completely_empty": [None, "", "   "],
        "normal_text": ["a", "b", "c"],
    }
    df = pd.DataFrame(data)
    res = QualityDetectionEngine.analyze(df, "test-empty-col", "empty_col.csv")
    heatmap = res["summary"].get("heatmap", [])

    col_map = {item["column_name"]: item for item in heatmap}
    empty_cell = col_map["completely_empty"]["cells"]["missing_value"]
    assert empty_cell["percentage"] == 100.0
    assert empty_cell["affected_count"] == 3
    assert empty_cell["severity"] == "high"
    assert col_map["completely_empty"]["overall_status"] == "high"


def test_heatmap_no_duplicate_records():
    """Verify dataset with zero duplicates reports 0% duplicate involvement for all columns."""
    data = {
        "col_a": [1, 2, 3, 4],
        "col_b": ["A", "B", "C", "D"],
        "col_c": [100.0, 200.0, 300.0, 400.0],
    }
    df = pd.DataFrame(data)
    res = QualityDetectionEngine.analyze(df, "test-no-dup", "no_dup.csv")
    heatmap = res["summary"].get("heatmap", [])

    for item in heatmap:
        dup_cell = item["cells"]["duplicate"]
        assert dup_cell["percentage"] == 0.0
        assert dup_cell["affected_count"] == 0
        assert dup_cell["severity"] == "healthy"
