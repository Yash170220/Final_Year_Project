# AI ESG Reporting System - Complete Guide

## Overview
Automated ESG (Environmental, Social, Governance) reporting system that ingests data, validates it, and prepares it for report generation.

---

## System Architecture

```
Upload File → Ingest → Match → Normalize → Validate → (Generate Report)
     ↓          ↓        ↓         ↓           ↓
   Excel/    Parse   Find    Convert    Check
   CSV/PDF   Data   Indicators  Units    Quality
```

---

## API Endpoints (11 total)

### Base URL: `http://localhost:8000`

All endpoints follow a consistent pattern: **POST** to trigger processing, **GET** to retrieve results.

#### Health
```
GET  /              → {"status": "running"}
GET  /health        → Health check
```

#### Ingestion (3 endpoints)
```
POST   /api/v1/ingest/upload              → Upload a file
GET    /api/v1/ingest/{upload_id}         → Status + headers + preview (first 10 rows)
DELETE /api/v1/ingest/{upload_id}         → Soft-delete upload
```

#### Matching (2 endpoints)
```
POST /api/v1/matching/{upload_id}         → Trigger matching (empty body)
                                            OR save reviews (body with reviews list)
GET  /api/v1/matching/{upload_id}         → Stats + all results + review queue
```

#### Normalization (2 endpoints)
```
POST /api/v1/normalization/{upload_id}    → Trigger normalization
GET  /api/v1/normalization/{upload_id}    → Summary + conversions + errors + data sample
                                            Supports ?limit=100&offset=0
```

#### Validation (2 endpoints)
```
POST /api/v1/validation/{upload_id}?industry=cement_industry
                                          → Run validation (empty body)
                                            OR save reviews (body with reviews list)
GET  /api/v1/validation/{upload_id}       → Summary + breakdowns + all errors + all warnings
```

**Interactive docs:** `http://localhost:8000/docs`

---

## Core Modules

### 1. Ingestion (`src/ingestion/`)
Reads Excel, CSV files and extracts data.

**Files:**
- `csv_parser.py` - Parses CSV (auto-detects delimiter, encoding)
- `excel_parser.py` - Parses Excel (.xlsx), handles merged cells, multi-sheet
- `base_parser.py` - Common parser interface
- `service.py` - Orchestrates parsing, saves to DB, generates preview

**Key service methods:**
- `ingest_file_from_upload()` - Full upload flow (parse → save → preview)
- `get_upload_details()` - Returns status + metadata + headers + preview rows

---

### 2. Matching (`src/matching/`)
Maps uploaded column names to standard ESG indicators.

**Files:**
- `rule_matcher.py` - Fast fuzzy string matching (~90% accuracy)
- `llm_matcher.py` - Groq LLM fallback for ambiguous headers
- `service.py` - Two-tier matching + review workflow

**Key service methods:**
- `match_headers()` - Match all headers for an upload
- `get_comprehensive_results()` - Stats + results + review queue in one call
- `approve_match()` - Accept or correct a match
- `get_best_match()` - Rule-first, then LLM fallback

**How it works:**
1. Rule matcher tries fuzzy match first (fast)
2. If confidence < 80%, falls back to LLM
3. Items with confidence < 85% go to review queue

---

### 3. Normalization (`src/normalization/`)
Converts all units to standard formats (e.g., kWh → MWh, kg → tonnes).

**Files:**
- `normalizer.py` - Unit conversion logic with factor lookup
- `service.py` - DB integration, unit detection from context

**Key service methods:**
- `normalize_data()` - Normalize all indicators for an upload
- `get_comprehensive_results()` - Summary + conversions + errors + data sample
- `detect_unit_from_context()` - Infers unit from header text and value magnitudes

**Conversion rules:** `data/validation-rules/conversion_factors.json`

---

### 4. Validation (`src/validation/`)
Checks data quality using 29 industry-specific rules.

**Files:**
- `engine.py` - Core validation logic (range, outlier, cross-field, temporal)
- `service.py` - DB integration, review workflow, comprehensive results

**Key service methods:**
- `validate_upload()` - Run all validations for an upload
- `get_comprehensive_results()` - Summary + breakdowns + errors + warnings
- `mark_error_as_reviewed()` - Mark false positives
- `calculate_final_pass_rate()` - Pass rate after reviews

**Validation types:**
- Range checks (e.g., cement emissions: 800-1100 kg CO2/tonne)
- Outlier detection (statistical z-score)
- Cross-field (e.g., Scope 1 + 2 + 3 = Total)
- Temporal consistency (monthly sums match annual)
- Category checks, null checks, precision checks

**Rules:** `data/validation-rules/validation_rules.json`

---

### 5. Generation (`src/generation/`)
**Status:** Not yet implemented (placeholder for RAG narrative generation).

---

## Shared Code (`src/common/`)

- `config.py` - Pydantic settings (database, redis, groq, app config)
- `database.py` - SQLAlchemy engine and session management
- `models.py` - Database models (Upload, MatchedIndicator, NormalizedData, ValidationResult, AuditLog)
- `schemas.py` - Pydantic request/response schemas for all endpoints

---

## Database Schema

**Tables:**
- `uploads` - File metadata (filename, type, status, file_metadata JSON)
- `matched_indicators` - Column → indicator mappings with confidence
- `normalized_data` - Converted values with units and conversion factors
- `validation_results` - Quality check results (pass/fail, severity, message)
- `audit_log` - All changes tracked for provenance

**Relationships:**
```
uploads → matched_indicators → normalized_data → validation_results
   ↓
audit_log (tracks all entities)
```

---

## Data Flow Example

**Input File (cement_plant.csv):**
```
| Plant | CO2 Emmissions | Energy Used |
|-------|---------------|-------------|
| A     | 1500 kg       | 4.2 GJ      |
```

**Step 1: Ingest** → `POST /api/v1/ingest/upload`
```json
{"upload_id": "uuid", "filename": "cement_plant.csv", "status": "completed", "detected_headers": ["Plant", "CO2 Emmissions", "Energy Used"]}
```

**Step 2: Match** → `POST /api/v1/matching/{upload_id}`
```json
{"status": "completed", "processed_count": 3}
```

**Step 3: Normalize** → `POST /api/v1/normalization/{upload_id}`
```json
{"status": "completed", "processed_count": 2}
```

**Step 4: Validate** → `POST /api/v1/validation/{upload_id}?industry=cement_industry`
```json
{"status": "completed", "errors_found": 1, "warnings_found": 0}
```

**View results** → `GET /api/v1/validation/{upload_id}`
```json
{
  "summary": {"total_records": 2, "records_with_errors": 1, "validation_pass_rate": 50.0},
  "errors": [{"rule_name": "cement_emission_range", "message": "Value 1500 outside range (800-1100)"}]
}
```

---

## Running the System

### 1. Setup
```bash
poetry install
cp .env.example .env
```

### 2. Start Database
```bash
# Option A: Docker
docker-compose up -d
poetry run alembic upgrade head

# Option B: Local PostgreSQL (Homebrew)
brew install postgresql@16
brew services start postgresql@16
/opt/homebrew/opt/postgresql@16/bin/createuser esg_user -P   # password: esg_password
/opt/homebrew/opt/postgresql@16/bin/createdb esg_db -O esg_user
# Then create tables:
poetry run python -c "from src.common.database import engine; from src.common.models import Base; Base.metadata.create_all(bind=engine)"
```

### 3. Start Server
```bash
poetry run uvicorn src.main:app --reload
```

### 4. Test
Open `http://localhost:8000/docs` in your browser.

---

## Testing

```bash
# Run all tests
poetry run pytest

# Specific module
poetry run pytest tests/test_validation.py -v

# With coverage
poetry run pytest --cov=src --cov-report=html
```

**Test files:**
- `test_ingestion.py` - File parsing + API endpoint tests
- `test_rule_matcher.py` - Fuzzy matching tests
- `test_llm_matcher.py` - LLM matching tests
- `test_matching_service.py` - Matching service + comprehensive results tests
- `test_normalizer.py` - Unit conversion tests
- `test_normalization_service.py` - Normalization service tests
- `test_validation.py` - Engine validation tests (rules, cross-field, integration)
- `test_validation_service.py` - Validation service + review workflow tests

---

## Key Configuration Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Dependencies (Poetry) |
| `.env` / `.env.example` | Environment variables (DB, Redis, Groq API) |
| `docker-compose.yml` | PostgreSQL + Redis services |
| `data/validation-rules/validation_rules.json` | 29 validation rules |
| `data/validation-rules/conversion_factors.json` | Unit conversion mappings |
| `data/validation-rules/synonym_dictionary.json` | Column name synonyms |

---

## Industry Rules Coverage

### Cement Industry (3 rules)
- Emission intensity: 800-1,100 kg CO2/tonne clinker
- Energy intensity: 2.9-4.5 GJ/tonne clinker
- Clinker ratio: 0.65-0.95

### Steel Industry (3 rules)
- BF-BOF emissions: 1,800-2,500 kg CO2/tonne
- EAF emissions: 400-600 kg CO2/tonne
- Energy intensity: 18-25 GJ/tonne

### Automotive Industry (3 rules)
- Manufacturing emissions: 4-12 tonnes CO2e/vehicle
- VOC emissions: 10-35 kg/vehicle
- Water consumption: 3-8 m3/vehicle

### Cross-Industry (8 rules)
- Scope totals consistency
- Temporal consistency
- Outlier detection
- Unit format validation
- Negative value checks
- Biogenic carbon, facility boundaries, emission factors

### Cross-Field (8 rules)
- Scope 1+2+3 = Total emissions
- Energy balance
- Production-energy correlation
- Waste material balance
- Water withdrawal vs discharge
- Renewable/total energy ratio

---

## Validation Review Workflow

1. **Run validation:** `POST /api/v1/validation/{upload_id}?industry=cement_industry`
2. **View results:** `GET /api/v1/validation/{upload_id}` → see all errors/warnings
3. **Review errors:** `POST /api/v1/validation/{upload_id}` with body:
   ```json
   {"reviews": [{"result_id": "uuid", "reviewed": true, "notes": "False positive"}]}
   ```
4. **Check status:** `GET /api/v1/validation/{upload_id}` → `summary.unreviewed_errors` should be 0
5. Export is unblocked when all errors are reviewed or corrected

---

## Project Structure

```
backend/
├── src/
│   ├── api/               # FastAPI endpoint files
│   │   ├── ingestion.py   # 3 endpoints (upload, get details, delete)
│   │   ├── matching.py    # 2 endpoints (process/review, get results)
│   │   ├── normalization.py # 2 endpoints (process, get results)
│   │   └── validation.py  # 2 endpoints (process/review, get results)
│   ├── ingestion/         # File parsing (Excel, CSV)
│   ├── matching/          # Column → indicator mapping
│   ├── normalization/     # Unit conversions
│   ├── validation/        # Quality checks (29 rules)
│   ├── generation/        # Placeholder for RAG
│   ├── common/            # Shared (models, schemas, config, database)
│   └── main.py            # App entry point
├── data/
│   └── validation-rules/  # Rules, conversions, synonyms (JSON)
├── tests/                 # pytest suite
├── docs/
│   ├── prd.md             # Product requirements
│   └── SYSTEM_GUIDE.md    # This file
├── pyproject.toml
├── docker-compose.yml
└── .env.example
```

---

## Quick Reference

```bash
# Start server
poetry run uvicorn src.main:app --reload

# Full pipeline (curl)
# 1. Upload
curl -X POST http://localhost:8000/api/v1/ingest/upload \
  -F "file=@data.csv" -F "facility_name=Plant A" -F "reporting_period=2024-01"

# 2. Match (use upload_id from step 1)
curl -X POST http://localhost:8000/api/v1/matching/{upload_id}

# 3. Normalize
curl -X POST http://localhost:8000/api/v1/normalization/{upload_id}

# 4. Validate
curl -X POST "http://localhost:8000/api/v1/validation/{upload_id}?industry=cement_industry"

# 5. View results
curl http://localhost:8000/api/v1/validation/{upload_id}
```

---

**Last Updated:** 2026-02-21
**System Version:** 0.1.0
**Status:** Core modules complete (ingest, match, normalize, validate). Generation module pending.
