# Validation System Usage Guide

## Overview

The validation system provides comprehensive data quality checks for ESG reporting data across multiple industries.

## Components

1. **ValidationEngine** (`src/validation/engine.py`)
   - Core validation logic
   - Rule-based validation execution
   - Multiple validation types (range, category, outlier, temporal, etc.)

2. **ValidationService** (`src/validation/service.py`)
   - Database integration
   - Batch processing
   - Report generation
   - Audit logging

3. **Validation Rules** (`data/validation-rules/validation_rules.json`)
   - Industry-specific rules (cement, steel, automotive)
   - Cross-industry rules (scope classification, temporal consistency)
   - Data quality rules (completeness, precision)

## Quick Start

### 1. Using the Validation Engine Directly

```python
from pathlib import Path
from uuid import uuid4
from src.validation.engine import ValidationEngine, NormalizedRecord

# Initialize engine
rules_path = Path("data/validation-rules/validation_rules.json")
engine = ValidationEngine(str(rules_path))

# Create a record to validate
record = NormalizedRecord(
    id=uuid4(),
    indicator="Scope 1 GHG Emissions per tonne clinker",
    value=950.0,
    unit="kg CO₂/tonne",
    original_value=950.0,
    original_unit="kg CO₂/tonne"
)

# Validate single record
results = engine.validate_record(record, "cement_industry")

# Check results
if results:
    for result in results:
        print(f"❌ {result.rule_name}: {result.message}")
        print(f"   Severity: {result.severity}")
        print(f"   Citation: {result.citation}")
else:
    print("✅ All validations passed!")
```

### 2. Using the Validation Service (with Database)

```python
from src.validation.engine import ValidationEngine
from src.validation.service import ValidationService
from src.common.database import SessionLocal

# Initialize
engine = ValidationEngine("data/validation-rules/validation_rules.json")
db = SessionLocal()
service = ValidationService(engine, db)

# Validate an entire upload
upload_id = "your-upload-uuid"
summary = service.validate_upload(upload_id, "cement_industry")

print(f"Total records: {summary.total_records}")
print(f"Valid records: {summary.valid_records}")
print(f"Pass rate: {summary.validation_pass_rate}%")
print(f"Errors: {summary.records_with_errors}")
print(f"Warnings: {summary.records_with_warnings}")

# Get detailed errors
errors = service.get_validation_errors(upload_id)
for error in errors:
    print(f"❌ {error['rule_name']}: {error['message']}")

# Generate comprehensive report
report = service.generate_validation_report(upload_id)
print("\n📊 Validation Report:")
print(f"Summary: {report.summary}")
print(f"\n💡 Recommendations:")
for rec in report.recommendations:
    print(f"  - {rec}")
```

### 3. Using the API

#### Validate an Upload

```bash
curl -X POST "http://localhost:8000/api/v1/validation/validate/upload" \
  -H "Content-Type: application/json" \
  -d '{
    "upload_id": "your-upload-uuid",
    "industry": "cement_industry"
  }'
```

Response:
```json
{
  "total_records": 100,
  "valid_records": 85,
  "records_with_errors": 10,
  "records_with_warnings": 5,
  "validation_pass_rate": 90.0,
  "error_breakdown": {
    "cement_emission_range": 8,
    "detect_decimal_errors": 2
  },
  "warning_breakdown": {
    "cement_energy_range": 5
  }
}
```

#### Get Validation Report

```bash
curl -X GET "http://localhost:8000/api/v1/validation/upload/{upload_id}/report"
```

#### Get Only Errors

```bash
curl -X GET "http://localhost:8000/api/v1/validation/upload/{upload_id}/errors"
```

#### Get Only Warnings

```bash
curl -X GET "http://localhost:8000/api/v1/validation/upload/{upload_id}/warnings"
```

#### Validate Single Record

```bash
curl -X POST "http://localhost:8000/api/v1/validation/validate/record" \
  -H "Content-Type: application/json" \
  -d '{
    "record": {
      "id": "record-uuid",
      "indicator": "Scope 1 GHG Emissions per tonne clinker",
      "value": 950.0,
      "unit": "kg CO₂/tonne",
      "original_value": 950.0,
      "original_unit": "kg CO₂/tonne"
    },
    "industry": "cement_industry"
  }'
```

#### Get Rules Summary

```bash
curl -X GET "http://localhost:8000/api/v1/validation/rules/summary"
```

Response:
```json
{
  "total_rules": 20,
  "industries": ["cement_industry", "steel_industry", "automotive_industry", "cross_industry"],
  "rules_by_industry": {
    "cement_industry": 3,
    "steel_industry": 3,
    "automotive_industry": 3,
    "cross_industry": 8,
    "energy_utilities": 2,
    "data_quality": 2
  },
  "validation_types": ["range", "category_check", "outlier", "sum_check", "pattern_match", "null_check", "precision_check"]
}
```

## Validation Types

### 1. Range Check
Validates numeric values are within expected bounds.

```json
{
  "validation_type": "range",
  "parameters": {
    "min": 800,
    "max": 1100,
    "unit": "kg CO₂/tonne"
  }
}
```

### 2. Category Check
Validates values belong to allowed categories.

```json
{
  "validation_type": "category_check",
  "parameters": {
    "allowed_sources": ["stationary combustion", "mobile combustion", "process emissions"]
  }
}
```

### 3. Outlier Detection
Statistical outlier detection using z-scores.

```json
{
  "validation_type": "outlier",
  "parameters": {
    "z_score_threshold": 3.0
  }
}
```

### 4. Temporal Consistency
Validates monthly data sums to annual totals.

```json
{
  "validation_type": "sum_check",
  "parameters": {
    "tolerance": 0.02
  }
}
```

### 5. Pattern Matching
Validates string patterns (e.g., unit formats).

```json
{
  "validation_type": "pattern_match",
  "parameters": {
    "allowed_patterns": ["kg CO₂", "tonnes CO₂e", "GJ", "MWh"]
  }
}
```

## Industry-Specific Rules

### Cement Industry
- Emission intensity: 800-1,100 kg CO₂/tonne clinker
- Energy intensity: 2.9-4.5 GJ/tonne clinker
- Clinker ratio: 0.65-0.95

### Steel Industry
- BF-BOF emissions: 1,800-2,500 kg CO₂/tonne crude steel
- EAF emissions: 400-600 kg CO₂/tonne crude steel
- Energy intensity: 18-25 GJ/tonne crude steel

### Automotive Industry
- Manufacturing emissions: 4-12 tonnes CO₂e/vehicle
- VOC emissions: 10-35 kg VOC/vehicle
- Water consumption: 3-8 m³/vehicle

## Adding Custom Rules

To add a new validation rule, edit `data/validation-rules/validation_rules.json`:

```json
{
  "your_industry": {
    "your_rule": {
      "rule_name": "your_rule_name",
      "description": "Clear description of what this validates",
      "indicator": "Specific indicator name or empty for all",
      "validation_type": "range|category_check|outlier|sum_check|pattern_match",
      "parameters": {
        "min": 100,
        "max": 500,
        "unit": "your_unit"
      },
      "severity": "error",
      "citation": "Authoritative source reference",
      "error_message": "Clear error message for users",
      "suggested_fixes": [
        "First suggestion to fix the issue",
        "Second suggestion",
        "Third suggestion"
      ]
    }
  }
}
```

## Testing

Run validation tests:

```bash
# Run all validation tests
pytest tests/test_validation.py tests/test_validation_service.py -v

# Run with coverage
pytest tests/test_validation.py tests/test_validation_service.py --cov=src/validation --cov-report=html

# Run specific test
pytest tests/test_validation.py::TestValidationEngine::test_range_check_above_maximum -v
```

## Best Practices

1. **Always validate after normalization** - Validate normalized data, not raw data
2. **Use appropriate severity levels** - Errors for critical issues, warnings for recommendations
3. **Provide actionable suggestions** - Include suggested_fixes in all rules
4. **Cite authoritative sources** - Reference industry standards and research
5. **Review validation reports** - Don't just check pass/fail, review the recommendations
6. **Update rules regularly** - Keep validation rules current with industry standards

## Troubleshooting

### Issue: No rules found
**Solution:** Ensure `validation_rules.json` exists at the correct path:
```bash
ls data/validation-rules/validation_rules.json
```

### Issue: All records failing validation
**Solution:** Check if the industry parameter matches your rules file structure:
- Use `"cement_industry"` not `"cement"`
- Use `"steel_industry"` not `"steel"`

### Issue: Outlier detection not working
**Solution:** Outlier detection requires at least 3 records. Use `validate_batch` instead of `validate_record`.

### Issue: Temporal consistency always failing
**Solution:** Ensure monthly keys match exactly (case-sensitive) and check tolerance parameter.

## Performance Considerations

- **Batch validation** is more efficient than individual record validation
- **Index your rules** by using the engine's built-in indexing
- **Database connection pooling** is configured in `src/common/database.py`
- **Bulk inserts** are used for saving validation results

## API Documentation

Full API documentation available at:
```
http://localhost:8000/docs
```

After starting the server:
```bash
uvicorn src.main:app --reload
```
