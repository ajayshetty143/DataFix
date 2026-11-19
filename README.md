# DataFix

> Automated Data Quality, Validation, Profiling & Intelligent Remediation Platform.

This repository contains the full-stack architecture for DataFix, completed through **Phase 3 (Intelligent Data Quality Detection Engine)**.

---

## Architecture Overview

```
DataFix/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── health.py             # GET /api/v1/health (Health check & DB status)
│   │   │   │   │   └── datasets.py           # Upload, preview, list, and POST/GET quality analysis
│   │   │   │   └── api.py                    # Aggregated v1 API router
│   │   ├── core/
│   │   │   ├── config.py                     # Pydantic Settings, CORS, Upload limits & extensions
│   │   │   └── database.py                   # SQLAlchemy 2.0 engine, SessionLocal & SQLite lifecycle
│   │   ├── models/
│   │   │   └── dataset.py                    # Dataset SQLAlchemy Model (profile_json, quality_json)
│   │   ├── schemas/
│   │   │   ├── health.py                     # Health check schema
│   │   │   ├── dataset.py                    # DatasetProfileResponse, PaginatedPreviewResponse, Stats
│   │   │   └── quality.py                    # QualityReportResponse, QualityIssue, QualitySummary
│   │   ├── services/
│   │   │   ├── detection/                    # Phase 3 Modular Detection Engine
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py                   # Common QualityIssue model and dataclasses
│   │   │   │   ├── missing_detector.py       # Dimension 1: Null, empty, whitespace & placeholder detection
│   │   │   │   ├── duplicate_detector.py     # Dimension 2: Exact & potential near-duplicate detection
│   │   │   │   ├── format_detector.py        # Dimension 3: Email, date, numeric format violations
│   │   │   │   ├── inconsistency_detector.py # Dimension 4: Categorical casing/whitespace clusters
│   │   │   │   ├── anomaly_detector.py       # Dimension 5: Statistical anomalies (IQR & Z-score)
│   │   │   │   └── engine.py                 # Coordinator orchestrating all 5 detectors
│   │   │   ├── profiler.py                   # Data profiling: type inference, null stats, numerical stats
│   │   │   └── dataset_service.py            # File validation, storage, pandas loader & paginator
│   │   └── main.py                           # FastAPI application factory & startup migration
│   ├── tests/
│   │   ├── sample_customers.csv              # Test fixture with missing values
│   │   ├── sample_products.xlsx              # Test fixture Excel spreadsheet
│   │   ├── messy_dataset.csv                 # Comprehensive Phase 3 test dataset for all 5 detectors
│   │   ├── test_health.py                    # Automated health API test suite
│   │   ├── test_datasets.py                  # Test suite for uploads, profiling, pagination
│   │   └── test_quality.py                   # Comprehensive tests for all 5 quality detection categories
│   ├── uploads/                              # Dedicated directory preserving original files
│   ├── .env.example                          # Backend environment template
│   ├── .env                                  # Active backend environment
│   ├── requirements.txt                      # Backend Python dependencies
│   └── run.py                                # Development server entry point
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx                    # Header bar with real-time status indicator
│   │   │   ├── HealthStatus.jsx              # Diagnostics card & backend latency tester
│   │   │   ├── FileUploadZone.jsx            # Drag-and-drop file upload with progress & validation
│   │   │   ├── DatasetOverview.jsx           # Metrics summary (rows, columns, size, upload date)
│   │   │   ├── QualityDashboard.jsx          # Phase 3 Data Quality Analysis Dashboard & Inspector
│   │   │   ├── ColumnProfilingTable.jsx      # Filterable schema table (data types, missing %, stats)
│   │   │   └── DatasetPreviewTable.jsx       # Paginated table viewer with page size & streaming
│   │   ├── services/
│   │   │   └── api.js                        # Axios client with upload progress & endpoints
│   │   ├── App.jsx                           # Main application container with tabbed views
│   │   ├── index.css                         # Tailwind base & utilities
│   │   └── main.jsx                          # React 18 DOM mount point
│   ├── .env.example                          # Frontend environment template
│   ├── .env                                  # Active frontend environment
│   ├── package.json                          # React 18, Vite, Tailwind CSS, Lucide, Axios
│   ├── postcss.config.js                     # PostCSS plugins
│   ├── tailwind.config.js                    # Tailwind design tokens
│   └── vite.config.js                        # Vite dev server with proxy
│
├── .gitignore                                # Workspace Git ignore definitions
├── start-backend.bat                         # One-click Windows startup script for backend
├── start-frontend.bat                        # One-click Windows startup script for frontend
└── README.md                                 # Complete project documentation
```

---

## Phase 3 Features: 5 Detection Dimensions

1. **Missing Value Detection (`missing_detector.py`):**
   - Identifies `null`, `NaN`, empty strings `""`, whitespace-only strings (`"   "`, `"\t"`), and placeholder tokens (`"N/A"`, `"NA"`, `"null"`, `"unknown"`, `"-"`, `"`?`"`).
   - Reports exact 1-based row references, counts, and percentages per column.
   - Assigns severity based on impact (`critical` for >50%, `warning` for >15%, `info` for isolated).

2. **Duplicate Detection (`duplicate_detector.py`):**
   - Detects exact duplicate rows across all columns.
   - Detects duplicate records matching across all feature columns (excluding primary key IDs).
   - Detects potential near-duplicates differing only in casing, padding, or punctuation.
   - **Zero mutation:** Never modifies, drops, or merges records.

3. **Invalid Format Detection (`format_detector.py`):**
   - **False positive avoidance:** Does NOT assume every string column is an email or date. Evaluates column semantic context and pattern prevalence.
   - Detects invalid email addresses (missing `@`, double `@@`, missing domain/TLD).
   - Detects invalid and unparseable dates (e.g. `2023-13-45`, `not_a_date`, out-of-range calendar years).
   - Detects non-numeric characters inside numeric string fields.

4. **Inconsistency Detection (`inconsistency_detector.py`):**
   - Normalizes categorical string values (`strip()`, internal space collapse, `lower()`).
   - Flags clusters with multiple distinct representations (e.g. `Bangalore`, `bangalore`, `BANGALORE`).
   - Suggests standardization based on highest frequency or standard Title Case.

5. **Statistical Anomaly Detection (`anomaly_detector.py`):**
   - Implements IQR (Interquartile Range) bounds: $[Q1 - 1.5 \times IQR, Q3 + 1.5 \times IQR]$.
   - Implements Z-Score threshold ($|Z| > 3.0$).
   - **Safeguards:** Safely handles small sample sizes ($N < 4$) and constant columns ($\sigma = 0$) without division by zero.
   - Flags anomalies for human review rather than treating them automatically as errors.

6. **Results Interface & Quality Dashboard (`QualityDashboard.jsx`):**
   - Overall deterministic Data Quality Score (0 to 100).
   - Issues grouped by category with interactive filter pills.
   - Severity distribution: `Critical`, `Warning`, `Informational`.
   - Affected row counts, percentages, and affected column counters.
   - Detailed Issue Inspection Panel showing row references, flagged values, and recommendations.
   - "Inspect Records in Data Preview" button linking directly to the paginated table.

---

## Quick Start & Run Instructions

### 1. Start the Backend

```powershell
cd E:\Hackathon\DataFix\backend
.\venv\Scripts\activate
python run.py
```
- **Backend API:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Check Endpoint:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)

### 2. Start the Frontend

```powershell
cd E:\Hackathon\DataFix\frontend
npm run dev
```
- **Frontend UI App:** [http://localhost:5173](http://localhost:5173)

---

## Testing & Verification

### Run Automated Backend Pytest Suite

```powershell
cd E:\Hackathon\DataFix\backend
.\venv\Scripts\pytest.exe -v tests/
```

**Results (15 of 15 tests passed):**
```
tests/test_datasets.py::test_upload_csv_dataset[asyncio] PASSED          [  6%]
tests/test_datasets.py::test_upload_excel_dataset[asyncio] PASSED        [ 13%]
tests/test_datasets.py::test_paginated_preview[asyncio] PASSED           [ 20%]
tests/test_datasets.py::test_upload_invalid_extension[asyncio] PASSED    [ 26%]
tests/test_datasets.py::test_upload_empty_file[asyncio] PASSED           [ 33%]
tests/test_datasets.py::test_dataset_list[asyncio] PASSED                [ 40%]
tests/test_health.py::test_root[asyncio] PASSED                          [ 46%]
tests/test_health.py::test_health_check[asyncio] PASSED                  [ 53%]
tests/test_quality.py::test_missing_detector PASSED                      [ 60%]
tests/test_quality.py::test_duplicate_detector PASSED                    [ 66%]
tests/test_quality.py::test_format_detector_and_false_positives PASSED   [ 73%]
tests/test_quality.py::test_inconsistency_detector PASSED                [ 80%]
tests/test_quality.py::test_statistical_anomaly_detector_and_constant_columns PASSED [ 86%]
tests/test_quality.py::test_empty_dataset_safety PASSED                  [ 93%]
tests/test_quality.py::test_quality_analysis_api_endpoint[asyncio] PASSED [100%]

============================= 15 passed in 1.88s ==============================
```

### Build Frontend Production Bundle

```powershell
cd E:\Hackathon\DataFix\frontend
npm run build
```

**Results:**
```
vite v5.4.21 building for production...
✓ 1658 modules transformed.
dist/index.html                   0.54 kB
dist/assets/index-F_rIi8Pw.css   28.68 kB
dist/assets/index-BWaf29dV.js   268.12 kB
✓ built in 5.47s (0 errors)
```

---

## Status
- [x] Phase 1: Modular Foundation & Health Check (Complete)
- [x] Phase 2: Smart Dataset Upload & Preview (Complete)
- [x] Phase 3: Intelligent Data Quality Detection Engine (Complete)
- [ ] Phase 4: Awaiting user approval to proceed.
