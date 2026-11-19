# DataFix

> Automated Data Quality, Validation, Profiling & Remediation Platform.

This repository contains the full-stack architecture for DataFix, completed through **Phase 2 (Smart Dataset Upload and Preview)**.

---

## Architecture Overview

```
DataFix/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── health.py          # GET /api/v1/health (Health check & DB status)
│   │   │   │   │   └── datasets.py        # POST /upload, GET /{id}, GET /{id}/preview, GET /
│   │   │   │   └── api.py                 # Aggregated v1 API router
│   │   ├── core/
│   │   │   ├── config.py                  # Pydantic Settings, CORS, Upload limits & extensions
│   │   │   └── database.py                # SQLAlchemy 2.0 engine, SessionLocal & SQLite lifecycle
│   │   ├── models/
│   │   │   └── dataset.py                 # Dataset SQLAlchemy Model
│   │   ├── schemas/
│   │   │   ├── health.py                  # Health check schema
│   │   │   └── dataset.py                 # DatasetProfileResponse, PaginatedPreviewResponse, Stats
│   │   ├── services/
│   │   │   ├── profiler.py                # Data profiling: type inference, null stats, numerical stats
│   │   │   └── dataset_service.py         # File validation, storage, pandas loader & paginator
│   │   └── main.py                        # FastAPI application factory, CORS middleware & lifespan
│   ├── tests/
│   │   ├── sample_customers.csv           # Test fixture with missing values and mixed types
│   │   ├── sample_products.xlsx           # Test fixture Excel spreadsheet
│   │   ├── test_health.py                 # Automated health API test suite
│   │   └── test_datasets.py               # Complete test suite for uploads, profiling, pagination
│   ├── uploads/                           # Dedicated directory preserving original files
│   ├── .env.example                       # Backend environment template
│   ├── .env                               # Active backend environment
│   ├── requirements.txt                   # Backend Python dependencies
│   └── run.py                             # Development server entry point
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx                 # Application navigation bar with status indicator
│   │   │   ├── HealthStatus.jsx           # Diagnostics card & backend latency tester
│   │   │   ├── FileUploadZone.jsx         # Drag-and-drop file upload with progress & validation
│   │   │   ├── DatasetOverview.jsx        # Metrics summary (rows, columns, size, upload date)
│   │   │   ├── ColumnProfilingTable.jsx   # Filterable schema table (data types, missing %, stats)
│   │   │   └── DatasetPreviewTable.jsx    # Paginated table viewer with page size & streaming
│   │   ├── services/
│   │   │   └── api.js                     # Axios HTTP client with upload progress & endpoints
│   │   ├── App.jsx                        # Main application container
│   │   ├── index.css                      # Tailwind base & utilities
│   │   └── main.jsx                       # React 18 DOM mount point
│   ├── .env.example                       # Frontend environment template
│   ├── .env                               # Active frontend environment
│   ├── package.json                       # React 18, Vite, Tailwind CSS, Lucide, Axios
│   ├── postcss.config.js                  # PostCSS plugins
│   ├── tailwind.config.js                 # Tailwind design tokens
│   └── vite.config.js                     # Vite dev server with proxy
│
├── .gitignore                             # Workspace Git ignore definitions
├── start-backend.bat                      # One-click Windows startup script for backend
├── start-frontend.bat                     # One-click Windows startup script for frontend
└── README.md                              # Complete project documentation
```

---

## Phase 2 Features Implemented

1. **Upload CSV and Excel (.xlsx) Files:**
   - Supported extensions: `.csv`, `.xlsx`, `.xls`.
   - Validates maximum file size of **20 MB**.
   - Preserves the exact original uploaded file byte-for-byte in `backend/uploads/` with a unique UUID prefix.

2. **Smart Column Profiling:**
   - Semantic type identification (`integer`, `float`, `string`, `datetime`, `boolean`).
   - Missing-value count and missing-value percentage for every column.
   - Descriptive numerical statistics (Mean, Median, Minimum, Maximum, Standard Deviation).
   - Cardinality / unique count per column.

3. **Paginated Dataset Preview:**
   - Streamed pagination (`page` and `page_size` from 1 to 100).
   - Avoids loading entire large files into frontend memory.
   - Preserves row index and cleans `NaN`/`Infinity` values for strict JSON serialization.

4. **Polished Drag-and-Drop Frontend:**
   - Drag-and-drop zone with drag-over animations.
   - Upload progress percentage bar.
   - File size & type client-side pre-validation.
   - Loading skeletons and clear error states.
   - Searchable and filterable column profiling table.
   - Tab switching between "Dataset Preview" and "Column Schema & Stats".
   - Previously uploaded datasets history drawer.

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

**Output:**
```
tests/test_datasets.py::test_upload_csv_dataset[asyncio] PASSED          [ 12%]
tests/test_datasets.py::test_upload_excel_dataset[asyncio] PASSED        [ 25%]
tests/test_datasets.py::test_paginated_preview[asyncio] PASSED           [ 37%]
tests/test_datasets.py::test_upload_invalid_extension[asyncio] PASSED    [ 50%]
tests/test_datasets.py::test_upload_empty_file[asyncio] PASSED           [ 62%]
tests/test_datasets.py::test_dataset_list[asyncio] PASSED                [ 75%]
tests/test_health.py::test_root[asyncio] PASSED                          [ 87%]
tests/test_health.py::test_health_check[asyncio] PASSED                  [100%]
============================== 8 passed in 1.28s ==============================
```

### Build Frontend Production Bundle

```powershell
cd E:\Hackathon\DataFix\frontend
npm run build
```

**Output:**
```
vite v5.4.21 building for production...
✓ 1657 modules transformed.
dist/index.html                   0.54 kB
dist/assets/index-CTS6jz7K.css   25.97 kB
dist/assets/index-C_hLrlH5.js   249.82 kB
✓ built in 3.61s
```

---

## Status
- [x] Phase 1: Modular Foundation & Health Check (Complete)
- [x] Phase 2: Smart Dataset Upload & Preview (Complete)
- [ ] Phase 3: Awaiting user approval to proceed.
