import pytest
import pandas as pd
from app.services.detection.inconsistency_detector import detect_inconsistencies
from app.services.detection.anomaly_detector import detect_statistical_anomalies, is_identifier_or_discrete_code
from app.services.detection.engine import QualityDetectionEngine
from app.services.detection.heatmap import generate_quality_heatmap


# =============================================================================
# ISSUE 1 REGRESSION TESTS: CATEGORICAL INCONSISTENCY ACCURACY
# =============================================================================

def test_categorical_inconsistency_city_example():
    """
    Test exact prompt scenario:
    - Chennai: 14
    - Chennai : 1
    - Bengaluru: 20
    - bengaluru: 1
    Total rows = 36.
    Affected row count must be EXACTLY 2 (the 2 non-canonical entries), NOT 36.
    """
    cities = (
        ["Chennai"] * 14 +
        ["Chennai "] * 1 +
        ["Bengaluru"] * 20 +
        ["bengaluru"] * 1
    )
    df = pd.DataFrame({"city": cities})
    issues = detect_inconsistencies(df)

    assert len(issues) == 1
    issue = issues[0]
    assert issue.column == "city"
    assert issue.category == "inconsistency"

    # Exactly 2 non-canonical rows should be affected
    assert issue.affected_count == 2
    assert len(issue.row_indices) == 2

    # Row 15 (1-based for "Chennai ") and Row 36 (1-based for "bengaluru")
    assert 15 in issue.row_indices
    assert 36 in issue.row_indices

    # Diagnostic metadata must retain full cluster evidence
    clusters = issue.metadata["clusters"]
    assert len(clusters) == 2

    chennai_cluster = next(c for c in clusters if c["normalized_key"] == "chennai")
    assert chennai_cluster["canonical"] == "Chennai"
    assert chennai_cluster["total_cluster_rows"] == 15
    assert chennai_cluster["affected_row_count"] == 1
    assert chennai_cluster["non_canonical_variations"] == ["Chennai "]

    bengaluru_cluster = next(c for c in clusters if c["normalized_key"] == "bengaluru")
    assert bengaluru_cluster["canonical"] == "Bengaluru"
    assert bengaluru_cluster["total_cluster_rows"] == 21
    assert bengaluru_cluster["affected_row_count"] == 1
    assert bengaluru_cluster["non_canonical_variations"] == ["bengaluru"]

    # Problematic sample values must only contain the non-canonical variants
    assert set(issue.sample_values) == {"Chennai ", "bengaluru"}


def test_categorical_inconsistency_status_example():
    """
    Test status categorical inconsistency:
    - active: 18, Active: 2, ACTIVE: 1
    - pending: 25, PENDING: 2
    Total rows = 48.
    Non-canonical count = (2 + 1) + 2 = 5 rows.
    """
    statuses = (
        ["active"] * 18 +
        ["Active"] * 2 +
        ["ACTIVE"] * 1 +
        ["pending"] * 25 +
        ["PENDING"] * 2
    )
    df = pd.DataFrame({"status": statuses})
    issues = detect_inconsistencies(df)

    assert len(issues) == 1
    issue = issues[0]
    assert issue.column == "status"
    assert issue.affected_count == 5
    assert len(issue.row_indices) == 5

    clusters = issue.metadata["clusters"]
    active_cluster = next(c for c in clusters if c["normalized_key"] == "active")
    assert active_cluster["canonical"] == "active"
    assert active_cluster["affected_row_count"] == 3
    assert set(active_cluster["non_canonical_variations"]) == {"Active", "ACTIVE"}

    pending_cluster = next(c for c in clusters if c["normalized_key"] == "pending")
    assert pending_cluster["canonical"] == "pending"
    assert pending_cluster["affected_row_count"] == 2
    assert pending_cluster["non_canonical_variations"] == ["PENDING"]


def test_categorical_inconsistency_product_category_example():
    """
    Test product_category categorical inconsistency:
    - Electronics: 30, electronics: 3, ELECTRONICS: 1
    - Home Appliances: 15, home appliances: 2
    Total rows = 51.
    Non-canonical count = (3 + 1) + 2 = 6 rows.
    """
    categories = (
        ["Electronics"] * 30 +
        ["electronics"] * 3 +
        ["ELECTRONICS"] * 1 +
        ["Home Appliances"] * 15 +
        ["home appliances"] * 2
    )
    df = pd.DataFrame({"product_category": categories})
    issues = detect_inconsistencies(df)

    assert len(issues) == 1
    issue = issues[0]
    assert issue.column == "product_category"
    assert issue.affected_count == 6
    assert len(issue.row_indices) == 6


# =============================================================================
# ISSUE 2 REGRESSION TESTS: NUMERIC IDENTIFIER EXCLUSION & MEASUREMENTS
# =============================================================================

def test_numeric_identifiers_and_phones_excluded_from_anomalies():
    """
    Verify numeric phone numbers, customer IDs, and zip codes are NOT flagged
    as statistical distribution anomalies (IQR/Z-score).
    """
    data = {
        "customer_id": [10001, 10002, 10003, 10004, 10005, 999999],  # 999999 is high ID, NOT anomaly
        "user_id": [1, 2, 3, 4, 5, 6],
        "phone_number": [9876543210, 9876543211, 9876543212, 9876543213, 1234567890, 9876543219],
        "mobile_no": [9123456780, 9123456781, 9123456782, 9123456783, 9123456784, 9999999999],
        "zip_code": [560001, 560002, 560003, 560004, 560005, 110001],
        "account_no": [1122334455, 1122334456, 1122334457, 1122334458, 9988776655, 1122334459],
    }
    df = pd.DataFrame(data)

    # All helper tests
    for col in df.columns:
        assert is_identifier_or_discrete_code(col, df[col]) is True, f"{col} should be recognized as an identifier!"

    # Anomaly detector must produce 0 issues for all these columns
    issues = detect_statistical_anomalies(df)
    assert len(issues) == 0, f"Identifier columns must not be flagged as outliers! Flagged: {[i.column for i in issues]}"


def test_measurements_age_and_purchase_amount_anomaly_detection_preserved():
    """
    CRITICAL: Confirm genuine continuous measurements like 'age' and 'purchase_amount'
    continue to detect extreme statistical outliers via IQR and Z-scores.
    """
    data = {
        "age": [25, 26, 27, 28, 29, 30, 28, 26, 250],  # Outlier 250
        "purchase_amount": [50.0, 55.0, 52.0, 48.0, 53.0, 51.0, 49.0, 54.0, 99999.0],  # Outlier 99999.0
    }
    df = pd.DataFrame(data)

    assert is_identifier_or_discrete_code("age", df["age"]) is False
    assert is_identifier_or_discrete_code("purchase_amount", df["purchase_amount"]) is False

    issues = detect_statistical_anomalies(df)
    flagged_cols = {i.column for i in issues}

    assert "age" in flagged_cols, "Age outlier (250) must be detected!"
    assert "purchase_amount" in flagged_cols, "Purchase amount outlier (99999.0) must be detected!"

    age_issue = next(i for i in issues if i.column == "age")
    assert 9 in age_issue.row_indices  # Row 9 is 250

    purchase_issue = next(i for i in issues if i.column == "purchase_amount")
    assert 9 in purchase_issue.row_indices  # Row 9 is 99999.0


# =============================================================================
# HEATMAP ACCURACY & RECONCILIATION TESTS
# =============================================================================

def test_heatmap_reflects_corrected_categorical_counts():
    """
    Confirm heatmap inconsistency percentage uses corrected non-canonical row counts
    (2 rows / 36 total rows = 5.6%), NOT the total cluster rows (36 rows / 100%).
    """
    cities = (
        ["Chennai"] * 14 +
        ["Chennai "] * 1 +
        ["Bengaluru"] * 20 +
        ["bengaluru"] * 1
    )
    df = pd.DataFrame({
        "customer_id": list(range(1001, 1037)),
        "city": cities,
        "purchase_amount": [100.0] * 35 + [999999.0],  # 1 outlier in purchase_amount
        "phone_number": [9876543210 + i for i in range(36)],  # Phone numbers
    })

    analysis = QualityDetectionEngine.analyze(df, "test-accuracy", "accuracy.csv")
    heatmap = analysis["summary"]["heatmap"]
    col_map = {item["column_name"]: item for item in heatmap}

    # 1. City Inconsistency: affected_count must be 2, percentage 5.6%
    city_incon = col_map["city"]["cells"]["inconsistency"]
    assert city_incon["affected_count"] == 2
    assert city_incon["percentage"] == 5.6
    assert city_incon["severity"] == "moderate"

    # 2. Customer ID: Statistical anomaly must be N/A
    cust_anomaly = col_map["customer_id"]["cells"]["statistical_anomaly"]
    assert cust_anomaly["is_applicable"] is False
    assert cust_anomaly["percentage"] is None
    assert cust_anomaly["severity"] == "na"

    # 3. Phone Number: Statistical anomaly must be N/A
    phone_anomaly = col_map["phone_number"]["cells"]["statistical_anomaly"]
    assert phone_anomaly["is_applicable"] is False
    assert phone_anomaly["percentage"] is None
    assert phone_anomaly["severity"] == "na"

    # 4. Purchase Amount: Statistical anomaly must be applicable and detected (1 row = 2.8%)
    purchase_anomaly = col_map["purchase_amount"]["cells"]["statistical_anomaly"]
    assert purchase_anomaly["is_applicable"] is True
    assert purchase_anomaly["affected_count"] == 1
    assert purchase_anomaly["percentage"] == 2.8
