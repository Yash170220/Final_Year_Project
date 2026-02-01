# Database Setup

## Initialize Database

1. Start PostgreSQL:
```bash
docker-compose up -d postgres
```

2. Create initial migration:
```bash
alembic revision --autogenerate -m "Initial schema"
```

3. Apply migrations:
```bash
alembic upgrade head
```

## Database Schema

- **uploads**: Tracks uploaded files
- **matched_indicators**: Entity matching results
- **normalized_data**: Processed and normalized data
- **validation_results**: Validation outcomes
- **audit_log**: Provenance tracking

All tables use UUID primary keys and include created_at/updated_at timestamps.
