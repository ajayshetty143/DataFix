import json
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.gemini_service import GeminiDetectiveService, extract_json_from_response, sanitize_secret
from app.schemas.ai_detective import AIDetectiveReportResponse, AIDetectiveRecommendation


# Sample test issues matching Phase 3 detection engine output
SAMPLE_ISSUES = [
    {
        "id": "ISS-001",
        "category": "missing_value",
        "severity": "warning",
        "column": "email",
        "title": "Missing Values in 'email'",
        "description": "Found 3 missing or empty values (20.0%) in column 'email'.",
        "row_indices": [1, 4, 8],
        "affected_count": 3,
        "sample_values": ["", None, "   "],
        "suggested_action": "Impute missing emails or prompt user during registration.",
    },
    {
        "id": "ISS-002",
        "category": "inconsistency",
        "severity": "warning",
        "column": "city",
        "title": "Categorical Inconsistencies in 'city'",
        "description": "Found 3 case/spacing variants for canonical value 'bangalore': Bangalore, bangalore, BANGALORE.",
        "row_indices": [0, 2, 5],
        "affected_count": 3,
        "sample_values": ["Bangalore", "bangalore", "BANGALORE"],
        "suggested_action": "Standardize to 'Bangalore'.",
    },
]


def test_sanitize_secret():
    """Verify API keys are never exposed in logs or strings."""
    secret = "AIzaSyFakeKey1234567890abcdefghijklm"
    text = f"Error connecting with key {secret} at endpoint."
    sanitized = sanitize_secret(text, secret)
    assert secret not in sanitized
    assert "[REDACTED_API_KEY]" in sanitized


def test_extract_json_markdown_fences():
    """Verify JSON extractor correctly handles markdown code fences."""
    raw = """```json
    {
      "executive_summary": "Test summary",
      "recommendations": []
    }
    ```"""
    data = extract_json_from_response(raw)
    assert data["executive_summary"] == "Test summary"
    assert data["recommendations"] == []


def test_extract_json_embedded_text():
    """Verify JSON extractor handles text surrounding a JSON object."""
    raw = """Here is the analysis:
    {
      "executive_summary": "Clean summary",
      "recommendations": []
    }
    Hope this helps!"""
    data = extract_json_from_response(raw)
    assert data["executive_summary"] == "Clean summary"


def test_zero_issues_no_api_call():
    """Verify datasets with no detected issues return a clean report without invoking Gemini API."""
    with patch("app.services.gemini_service.genai.Client") as mock_client:
        report = GeminiDetectiveService.analyze_issues(
            dataset_id="clean-ds-123",
            filename="clean.csv",
            total_rows=100,
            total_columns=5,
            issues=[],
            column_profiles=[],
        )
        assert report.total_recommendations == 0
        assert len(report.recommendations) == 0
        assert "zero data quality anomalies" in report.executive_summary.lower()
        mock_client.assert_not_called()


def test_missing_api_key_raises_400():
    """Verify service raises HTTP 400 when GEMINI_API_KEY is missing."""
    with patch("app.services.gemini_service.settings.GEMINI_API_KEY", ""):
        with pytest.raises(HTTPException) as exc_info:
            GeminiDetectiveService.analyze_issues(
                dataset_id="test-ds-1",
                filename="test.csv",
                total_rows=50,
                total_columns=4,
                issues=SAMPLE_ISSUES,
            )
        assert exc_info.value.status_code == 400
        assert "GEMINI_API_KEY" in exc_info.value.detail


def test_successful_gemini_response_and_association():
    """Verify successful Gemini response parsing, Pydantic validation, and 1:1 issue ID mapping."""
    mock_gemini_json = {
        "executive_summary": "The dataset contains standard data capture omissions and casing discrepancies.",
        "recommendations": [
            {
                "issue_id": "ISS-001",
                "issue_category": "missing_value",
                "explanation": "Missing email addresses prevent user notification and account verification.",
                "possible_root_cause": "Optional registration field during legacy sign-up flow.",
                "recommended_action": "Flag records for user verification or assign placeholder noreply email.",
                "recommendation_reason": "Maintains downstream notification channel integrity without deleting records.",
                "confidence": "High",
                "human_review_required": False,
            },
            {
                "issue_id": "ISS-002",
                "issue_category": "inconsistency",
                "explanation": "Mixed case city names will fragment grouping and geographical aggregations.",
                "possible_root_cause": "Unvalidated free-text input on frontend form.",
                "recommended_action": "Apply title-casing transformation: convert all variants to 'Bangalore'.",
                "recommendation_reason": "Standardizes categorical values with zero information loss.",
                "confidence": "High",
                "human_review_required": False,
            },
        ],
    }

    mock_response = MagicMock()
    mock_response.text = json.dumps(mock_gemini_json)

    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response

    with patch("app.services.gemini_service.settings.GEMINI_API_KEY", "dummy-api-key"), \
         patch("app.services.gemini_service.genai.Client", return_value=mock_client_instance):

        report = GeminiDetectiveService.analyze_issues(
            dataset_id="ds-success-1",
            filename="messy.csv",
            total_rows=10,
            total_columns=4,
            issues=SAMPLE_ISSUES,
        )

        assert isinstance(report, AIDetectiveReportResponse)
        assert report.total_recommendations == 2
        assert len(report.recommendations) == 2

        # Verify correct association with issue IDs
        rec1 = report.recommendations[0]
        assert rec1.issue_id == "ISS-001"
        assert rec1.confidence == "High"
        assert rec1.human_review_required is False
        assert "Missing email" in rec1.explanation

        rec2 = report.recommendations[1]
        assert rec2.issue_id == "ISS-002"
        assert rec2.confidence == "High"
        assert "Mixed case" in rec2.explanation


def test_malformed_ai_response_graceful_fallback():
    """Verify malformed Gemini output gracefully falls back to deterministic recommendations."""
    mock_response = MagicMock()
    mock_response.text = "This is not JSON at all! Just raw plain text explaining something."

    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.return_value = mock_response

    with patch("app.services.gemini_service.settings.GEMINI_API_KEY", "dummy-api-key"), \
         patch("app.services.gemini_service.genai.Client", return_value=mock_client_instance):

        report = GeminiDetectiveService.analyze_issues(
            dataset_id="ds-malformed-1",
            filename="messy.csv",
            total_rows=10,
            total_columns=4,
            issues=SAMPLE_ISSUES,
        )

        assert report.total_recommendations == 2
        assert len(report.recommendations) == 2

        # Both issues should have valid fallback recommendations matching their issue IDs
        ids = [r.issue_id for r in report.recommendations]
        assert "ISS-001" in ids
        assert "ISS-002" in ids
        for r in report.recommendations:
            assert r.confidence in ["High", "Medium", "Low"]
            assert isinstance(r.human_review_required, bool)


def test_gemini_api_unavailable_raises_503():
    """Verify that when all Gemini models fail or timeout, an HTTP 503 is returned."""
    mock_client_instance = MagicMock()
    mock_client_instance.models.generate_content.side_effect = Exception("504 DEADLINE_EXCEEDED. Gateway Timeout")

    with patch("app.services.gemini_service.settings.GEMINI_API_KEY", "dummy-api-key"), \
         patch("app.services.gemini_service.genai.Client", return_value=mock_client_instance):

        with pytest.raises(HTTPException) as exc_info:
            GeminiDetectiveService.analyze_issues(
                dataset_id="ds-timeout-1",
                filename="messy.csv",
                total_rows=10,
                total_columns=4,
                issues=SAMPLE_ISSUES,
            )
        assert exc_info.value.status_code == 503
        assert "temporarily unavailable" in exc_info.value.detail.lower()


@pytest.mark.anyio
async def test_ai_detective_endpoint_integration():
    """Integration test for POST and GET /datasets/{dataset_id}/ai-detective."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Upload a small dataset first
        csv_content = b"id,name,email\n1,Alice,alice@example.com\n2,Bob,\n3,Charlie,charlie@example.com\n"
        files = {"file": ("test_ai.csv", csv_content, "text/csv")}
        upload_resp = await ac.post("/api/v1/datasets/upload", files=files)
        assert upload_resp.status_code == 201
        dataset_id = upload_resp.json()["id"]

        # 2. Mock Gemini Detective response for endpoint call
        mock_gemini_json = {
            "executive_summary": "Dataset has minor missing email values.",
            "recommendations": [
                {
                    "issue_id": "ISS-001",
                    "issue_category": "missing_value",
                    "explanation": "Missing email value in row 2.",
                    "possible_root_cause": "Omission during registration.",
                    "recommended_action": "Contact user to supply email.",
                    "recommendation_reason": "Ensures valid communication address.",
                    "confidence": "High",
                    "human_review_required": True,
                }
            ],
        }

        mock_resp = MagicMock()
        mock_resp.text = json.dumps(mock_gemini_json)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_resp

        with patch("app.services.gemini_service.settings.GEMINI_API_KEY", "dummy-key"), \
             patch("app.services.gemini_service.genai.Client", return_value=mock_client):

            # Test POST /datasets/{id}/ai-detective
            post_resp = await ac.post(f"/api/v1/datasets/{dataset_id}/ai-detective")
            assert post_resp.status_code == 200
            data = post_resp.json()
            assert data["dataset_id"] == dataset_id
            assert data["total_recommendations"] >= 1
            assert "recommendations" in data

            # Test GET /datasets/{id}/ai-detective (cached)
            get_resp = await ac.get(f"/api/v1/datasets/{dataset_id}/ai-detective")
            assert get_resp.status_code == 200
            cached_data = get_resp.json()
            assert cached_data["dataset_id"] == dataset_id
            assert cached_data["total_recommendations"] == data["total_recommendations"]
