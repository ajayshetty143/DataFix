# DataFix

> Automated Data Quality, Validation & Remediation Platform.

This repository contains the full-stack foundation for DataFix, initialized in **Phase 1**.

---

## Architecture Overview

```
DataFix/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── endpoints/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   └── health.py          # Health check endpoint (/api/v1/health)
│   │   │   │   ├── __init__.py
│   │   │   │   └── api.py                 # Aggregated v1 API router
│   │   │   └── __init__.py
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py                  # Pydantic Settings & environment manager
│   │   │   └── database.py                # SQLAlchemy engine, SessionLocal & SQLite lifecycle
│   │   ├── models/                        # SQLAlchemy database models (ready for Phase 2)
│   │   ├── schemas/                       # Pydantic validation schemas
│   │   │   ├── __init__.py
│   │   │   └── health.py                  # Health API response schema
│   │   ├── services/                      # Business logic layer (ready for Phase 2)
│   │   ├── __init__.py
│   │   └── main.py                        # FastAPI application factory, CORS & startup lifecycle
│   ├── tests/
│   │   ├── __init__.py
│   │   └── test_health.py                 # Pytest async test suite
│   ├── .env.example                       # Backend configuration template
│   ├── .env                               # Active backend environment variables
│   ├── requirements.txt                   # Backend Python dependencies
│   └── run.py                             # Development server entry point
│
├── frontend/
│   ├── public/                            # Static assets
│   ├── src/
│   │   ├── components/
│   │   │   ├── Navbar.jsx                 # Application navigation bar with status indicator
│   │   │   └── HealthStatus.jsx           # Diagnostics card & backend latency tester
│   │   ├── services/
│   │   │   └── api.js                     # Axios HTTP client configured with environment base URL
│   │   ├── App.css
│   │   ├── App.jsx                        # Main application container
│   │   ├── index.css                      # Tailwind CSS base & utilities
│   │   └── main.jsx                       # React DOM entry point
│   ├── .env.example                       # Frontend configuration template
│   ├── .env                               # Active frontend environment variables
│   ├── index.html                         # Single-page application template
│   ├── package.json                       # Frontend dependencies & npm scripts
│   ├── postcss.config.js                  # PostCSS plugins (Tailwind & Autoprefixer)
│   ├── tailwind.config.js                 # Tailwind CSS design system configuration
│   └── vite.config.js                     # Vite dev server with proxy support
│
├── .gitignore                             # Workspace Git ignore definitions
├── start-backend.bat                      # One-click Windows startup script for backend
├── start-frontend.bat                     # One-click Windows startup script for frontend
└── README.md                              # Project documentation
```

---

## Tech Stack

| Layer | Technology | Version / Details |
|---|---|---|
| **Frontend** | React | `18.3.1` |
| **Bundler & Dev Server** | Vite | `5.4.14` |
| **Styling** | Tailwind CSS | `3.4.17` with PostCSS & Autoprefixer |
| **Icons** | Lucide React | `0.475.0` |
| **HTTP Client** | Axios | `1.7.9` |
| **Backend Framework** | FastAPI | `0.165.0` |
| **ASGI Web Server** | Uvicorn | `0.54.0` |
| **ORM & Database** | SQLAlchemy 2.0 + SQLite | `sqlite:///./datafix.db` |
| **Validation & Settings** | Pydantic v2 + Pydantic Settings | `2.14.3` / `2.16.3` |
| **Testing** | Pytest + AnyIO + HTTPX | `9.2.0` |

---

## Quick Start & Run Instructions

### 1. Backend (FastAPI + SQLite)

#### Option A: Quick Launch Script (Windows)
Double-click `start-backend.bat` in the project root.

#### Option B: Manual Terminal Execution
Open PowerShell or Command Prompt:

```powershell
# Navigate to backend
cd E:\Hackathon\DataFix\backend

# Activate the existing virtual environment
.\venv\Scripts\activate

# Run the server
python run.py
```

The backend starts at:
- **API Base:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Health Check Endpoint:** [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- **Interactive Swagger Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

### 2. Frontend (React + Vite + Tailwind CSS)

#### Option A: Quick Launch Script (Windows)
Double-click `start-frontend.bat` in the project root.

#### Option B: Manual Terminal Execution
In a second terminal window:

```powershell
# Navigate to frontend
cd E:\Hackathon\DataFix\frontend

# Start the Vite development server
npm run dev
```

The frontend will be available at:
- **UI Web App:** [http://localhost:5173](http://localhost:5173)

---

## Testing & Verification

### Running Backend Unit & Health Tests

```powershell
cd E:\Hackathon\DataFix\backend
.\venv\Scripts\pytest.exe -v tests/
```

**Expected output:**
```
tests/test_health.py::test_root[asyncio] PASSED                          [ 50%]
tests/test_health.py::test_health_check[asyncio] PASSED                  [100%]
============================== 2 passed in 0.66s ==============================
```

### Building Frontend Production Bundle

```powershell
cd E:\Hackathon\DataFix\frontend
npm run build
```

**Expected output:**
```
vite v5.4.21 building for production...
✓ 1653 modules transformed.
dist/index.html                   0.54 kB
dist/assets/index-D2Ow-uY6.css   17.65 kB
dist/assets/index-DfsV9KzT.js   222.04 kB
✓ built in 7.63s
```

---

## Health Check API Specification

- **Method:** `GET`
- **Route:** `/api/v1/health`
- **Response Format:**
```json
{
  "status": "healthy",
  "project": "DataFix API",
  "version": "0.1.0",
  "timestamp": "2026-11-19T05:50:53.303533Z",
  "database_status": "connected",
  "environment": "development",
  "details": {
    "database": "sqlite",
    "cors_origins": [
      "http://localhost:5173",
      "http://127.0.0.1:5173"
    ]
  }
}
```

---

## Status
- [x] Phase 1: Complete and Verified.
- [ ] Phase 2: Awaiting user approval to proceed.
