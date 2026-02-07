# Validation System - Quick Reference

## 🚀 Installation & Setup

```bash
# Already included in project dependencies
poetry install

# Start server
uvicorn src.main:app --reload
```

## 📋 Core Components

```python
# Import components
from src.validation import (
    ValidationEngine,      # Core validation logic
    ValidationService,     # Database integration
    ValidationSummary,     # Summary statistics
    ValidationReport,      # Comprehensive report
    NormalizedRecord,      # Input data model
    ValidationResult       # Output result model
)
```

## 💻 Quick Code Examples

### 1. Validate Single Record
```python
from src.validation import ValidationEngine, NormalizedRecord
from uuid import uuid4

engine = ValidationEngine("data/validation-rules/validation_rules.json")

record = NormalizedRecord(
    id=uuid4(),
    indicator="Scope 1 GHG Emissions per tonne clinker",
    value=950.0,
    unit="kg CO₂/tonne",
    original_value=950.0,
    original_unit="kg CO₂/tonne"
)

results = engine.validate_record(record, "cement_industry")
print("✅ Valid" if not results else f"❌ {len(results)} issues")
```

### 2. Validate with Database
```python
from src.validation import ValidationEngine, ValidationService
from src.common.database import SessionLocal

engine = ValidationEngine("data/validation-rules/validation_rules.json")
service = ValidationService(engine, SessionLocal())

summary = service.validate_upload(upload_id, "cement_industry")
print(f"Pass rate: {summary.validation_pass_rate}%")
```

### 3. Generate Report
```python
report = service.generate_validation_report(upload_id)
for recommendation in report.recommendations:
    print(f"💡 {recommendation}")
```

## 🌐 API Quick Reference

### Validate Upload
```bash
POST /api/v1/validation/validate/upload
Body: {"upload_id": "uuid", "industry": "cement_industry"}
```

### Get Report
```bash
GET /api/v1/validation/upload/{upload_id}/report
```

### Get Errors Only
```bash
GET /api/v1/validation/upload/{upload_id}/errors
```

### Get Warnings Only
```bash
GET /api/v1/validation/upload/{upload_id}/warnings
```

### Validate Single Record
```bash
POST /api/v1/validation/validate/record
Body: {
  "record": {...},
  "industry": "cement_industry"
}
```

### Get Rules Summary
```bash
GET /api/v1/validation/rules/summary
```

## 🏭 Industry Names

Use these exact strings:
- `cement_industry`
- `steel_industry`
- `automotive_industry`
- `cross_industry`
- `energy_utilities`
- `data_quality`

## 📊 Validation Types

| Type | Use Case | Parameters |
|------|----------|------------|
| `range` | Numeric bounds | min, max, unit |
| `category_check` | Enum validation | allowed_sources |
| `outlier` | Statistical outliers | z_score_threshold |
| `sum_check` | Part-to-whole | tolerance |
| `pattern_match` | String patterns | allowed_patterns |
| `null_check` | Required fields | required_fields |
| `precision_check` | Decimal places | max_decimal_places |

## 🎯 Common Validation Ranges

### Cement
- Emissions: 800-1,100 kg CO₂/tonne clinker
- Energy: 2.9-4.5 GJ/tonne clinker
- Clinker ratio: 0.65-0.95

### Steel
- BF-BOF: 1,800-2,500 kg CO₂/tonne crude steel
- EAF: 400-600 kg CO₂/tonne crude steel
- Energy: 18-25 GJ/tonne crude steel

### Automotive
- Manufacturing: 4-12 tonnes CO₂e/vehicle
- VOC: 10-35 kg VOC/vehicle
- Water: 3-8 m³/vehicle

## ⚙️ Severity Levels

```python
"error"   # Critical issues - must be fixed
"warning" # Potential issues - should review
```

## 📈 Response Structures

### ValidationSummary
```json
{
  "total_records": 100,
  "valid_records": 85,
  "records_with_errors": 10,
  "records_with_warnings": 5,
  "validation_pass_rate": 90.0,
  "error_breakdown": {"rule_name": count},
  "warning_breakdown": {"rule_name": count}
}
```

### ValidationResult
```json
{
  "data_id": "uuid",
  "rule_name": "cement_emission_range",
  "is_valid": false,
  "severity": "error",
  "message": "Value outside range...",
  "citation": "Andrew (2019)",
  "suggested_fixes": ["Fix 1", "Fix 2"],
  "actual_value": 1500.0,
  "expected_range": [800, 1100]
}
```

## 🧪 Testing Commands

```bash
# Run all validation tests
pytest tests/test_validation*.py -v

# Run with coverage
pytest tests/test_validation*.py --cov=src/validation

# Run specific test
pytest tests/test_validation.py::TestValidationEngine::test_range_check -v
```

## 🐛 Common Issues

### No rules loaded
```python
# Check file exists
from pathlib import Path
assert Path("data/validation-rules/validation_rules.json").exists()
```

### Wrong industry name
```python
# Check available industries
print(engine.rules.keys())
```

### Outliers not detected
```python
# Need 3+ records
results = engine.validate_batch(records, industry)  # Use batch!
```

## 💡 Pro Tips

1. **Always use batch validation** for multiple records (better performance)
2. **Check pass_rate**, not just error count
3. **Review warnings** even when no errors
4. **Use citations** to understand why rules exist
5. **Follow suggested_fixes** for quick resolution

## 📚 Full Documentation

- Usage Guide: `docs/validation_usage.md`
- Module README: `src/validation/README.md`
- Implementation: `docs/VALIDATION_IMPLEMENTATION.md`
- API Docs: `http://localhost:8000/docs`

## 🔗 File Locations

```
backend/
├── src/validation/
│   ├── __init__.py
│   ├── engine.py           # Core validation logic
│   ├── service.py          # Database integration
│   └── README.md
├── data/validation-rules/
│   └── validation_rules.json  # All validation rules
├── tests/
│   ├── test_validation.py
│   └── test_validation_service.py
└── docs/
    ├── validation_usage.md
    └── VALIDATION_IMPLEMENTATION.md
```

## 🎯 Integration Example

```python
# Full pipeline integration
def process_upload(file_path, upload_id, industry):
    # 1. Ingest
    data = ingest_service.parse(file_path)
    
    # 2. Match
    matched = matching_service.match(data)
    
    # 3. Normalize
    normalized = normalization_service.normalize(matched)
    
    # 4. Validate ✨
    summary = validation_service.validate_upload(upload_id, industry)
    
    # 5. Check pass rate
    if summary.validation_pass_rate < 95:
        return {"status": "needs_review", "summary": summary}
    
    # 6. Generate report
    report = generation_service.generate(normalized)
    return {"status": "success", "report": report}
```

---

**Need help?** Check the full documentation in `docs/validation_usage.md`
