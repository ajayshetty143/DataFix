import os
import pytest
import httpx
from app.main import app

CSV_PATH = "E:\\Hackathon\\DataFix\\backend\\tests\\sample_customers.csv"
EXCEL_PATH = "E:\\Hackathon\\DataFix\\backend\\tests\\sample_products.xlsx"


@pytest.mark.anyio
async def test_upload_csv_dataset():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with open(CSV_PATH, "rb") as f:
            files = {"file": ("sample_customers.csv", f, "text/csv")}
            resp = await client.post("/api/v1/datasets/upload", files=files)

        assert resp.status_code == 201, resp.text
        data = resp.json()

        assert data["filename"] == "sample_customers.csv"
        assert data["file_type"] == "csv"
        assert data["total_rows"] == 15
        assert data["total_columns"] == 8
        assert "id" in data

        # Check column profiling details
        profiles = {col["name"]: col for col in data["column_profiles"]}
        assert "id" in profiles
        assert "income" in profiles
        assert "email" in profiles
        assert "is_active" in profiles

        # Email missing count: 4 out of 15 (Bob, Evan, George, Kevin, Oscar -> Oscar has no email)
        assert profiles["email"]["null_count"] >= 4
        assert profiles["email"]["null_percentage"] > 0
        assert profiles["email"]["data_type"] == "string"

        # Numerical stats for income
        income_stats = profiles["income"]["stats"]
        assert income_stats is not None
        assert income_stats["min"] == 48000.0
        assert income_stats["max"] == 120000.75
        assert income_stats["mean"] > 0
        assert income_stats["median"] > 0

        # Boolean column
        assert profiles["is_active"]["data_type"] == "boolean"


@pytest.mark.anyio
async def test_upload_excel_dataset():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        with open(EXCEL_PATH, "rb") as f:
            files = {
                "file": (
                    "sample_products.xlsx",
                    f,
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            }
            resp = await client.post("/api/v1/datasets/upload", files=files)

        assert resp.status_code == 201, resp.text
        data = resp.json()

        assert data["filename"] == "sample_products.xlsx"
        assert data["file_type"] == "excel"
        assert data["total_rows"] == 12
        assert data["total_columns"] == 8

        profiles = {col["name"]: col for col in data["column_profiles"]}
        assert "price" in profiles
        assert profiles["price"]["is_numerical"] is True
        assert profiles["price"]["stats"]["min"] == 19.99
        assert profiles["price"]["stats"]["max"] == 449.00


@pytest.mark.anyio
async def test_paginated_preview():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # First upload
        with open(CSV_PATH, "rb") as f:
            files = {"file": ("sample_customers.csv", f, "text/csv")}
            up_resp = await client.post("/api/v1/datasets/upload", files=files)
        dataset_id = up_resp.json()["id"]

        # Page 1 with page_size=5
        resp_p1 = await client.get(f"/api/v1/datasets/{dataset_id}/preview?page=1&page_size=5")
        assert resp_p1.status_code == 200
        p1 = resp_p1.json()
        assert p1["page"] == 1
        assert p1["page_size"] == 5
        assert p1["total_rows"] == 15
        assert p1["total_pages"] == 3
        assert len(p1["rows"]) == 5
        assert p1["rows"][0]["_row_index"] == 1
        assert p1["rows"][4]["_row_index"] == 5

        # Page 2 with page_size=5
        resp_p2 = await client.get(f"/api/v1/datasets/{dataset_id}/preview?page=2&page_size=5")
        assert resp_p2.status_code == 200
        p2 = resp_p2.json()
        assert p2["page"] == 2
        assert len(p2["rows"]) == 5
        assert p2["rows"][0]["_row_index"] == 6


@pytest.mark.anyio
async def test_upload_invalid_extension():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("test.txt", b"hello world", "text/plain")}
        resp = await client.post("/api/v1/datasets/upload", files=files)
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.json()["detail"]


@pytest.mark.anyio
async def test_upload_empty_file():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        files = {"file": ("empty.csv", b"", "text/csv")}
        resp = await client.post("/api/v1/datasets/upload", files=files)
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"]


@pytest.mark.anyio
async def test_dataset_list():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/datasets")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

