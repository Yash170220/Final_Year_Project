# AI ESG Reporting System

An automated ESG (Environmental, Social, and Governance) reporting system powered by AI for data ingestion, processing, validation, and narrative generation.

## Features

- **Data Ingestion**: Parse Excel, CSV, and PDF files
- **Entity Matching**: Intelligent matching of data entities
- **Data Normalization**: Automatic unit conversion and standardization
- **Validation**: Rule-based data validation
- **RAG Narratives**: AI-generated reporting narratives

## Prerequisites

- Python 3.12+
- Poetry
- Docker & Docker Compose

## Setup Instructions

### 1. Clone and Navigate

```bash
cd backend
```

### 2. Install Dependencies

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Install project dependencies
poetry install
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration
```

### 4. Start Database Services

```bash
# Start PostgreSQL and Redis
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 5. Run Database Migrations

```bash
poetry run alembic upgrade head
```

### 6. Start Development Server

```bash
# Using Poetry
poetry run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Or activate virtual environment
poetry shell
uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`

API documentation: `http://localhost:8000/docs`

## Project Structure

```
backend/
├── src/
│   ├── ingestion/       # Data parsers (Excel, CSV, PDF)
│   ├── matching/        # Entity matching logic
│   ├── normalization/   # Unit conversion & standardization
│   ├── validation/      # Data validation rules
│   ├── generation/      # RAG narrative generation
│   └── common/          # Shared utilities, models, config
├── tests/               # Pytest test suite
├── data/
│   ├── sample-inputs/   # Test data files
│   └── validation-rules/ # JSON validation rules
├── docs/                # Documentation
├── pyproject.toml       # Poetry dependencies
└── docker-compose.yml   # Database services
```

## Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/test_ingestion.py
```

### Code Formatting

```bash
# Format code with Black
poetry run black src/ tests/

# Lint with Ruff
poetry run ruff check src/ tests/

# Type checking
poetry run mypy src/
```

## Docker Services

### Stop Services

```bash
docker-compose down
```

### View Logs

```bash
docker-compose logs -f
```

### Reset Database

```bash
docker-compose down -v
docker-compose up -d
```

## API Endpoints

- `GET /` - Health check
- `GET /docs` - Swagger UI documentation
- `POST /api/v1/ingest` - Upload and ingest data files
- `GET /api/v1/reports` - List reports
- `POST /api/v1/validate` - Validate data

## Contributing

1. Create a feature branch
2. Make your changes
3. Run tests and linting
4. Submit a pull request

## License

MIT
