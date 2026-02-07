# Validation Module

Comprehensive data validation system for ESG reporting with industry-specific rules and AI-powered quality checks.

## 📋 Features

- ✅ **20+ Validation Rules** across multiple industries
- 🏭 **Industry-Specific Rules** for cement, steel, automotive
- 🔍 **Multiple Validation Types**: range, category, outlier, temporal, pattern matching
- 📊 **Batch Processing** with cross-record validations
- 💾 **Database Integration** with audit logging
- 📈 **Comprehensive Reports** with actionable recommendations
- 🎯 **Severity Levels**: Errors vs. Warnings
- 📚 **Citations** from authoritative sources (GHG Protocol, IEA, EPA)

## 🏗️ Architecture

```
src/validation/
├── __init__.py          # Module exports
├── engine.py            # Core validation engine (rule execution)
└── service.py           # Service layer (database integration)

data/validation-rules/
└── validation_rules.json # Validation rule definitions

tests/
├── test_validation.py          # Engine tests
└── test_validation_service.py  # Service tests
```

## 🚀 Quick Start

### Basic Usage

```python
from src.validation.engine import ValidationEngine, NormalizedRecord
from uuid import uuid4

# Initialize engine
engine = ValidationEngine("data/validation-rules/validation_rules.json")

# Create record
record = NormalizedRecord(
    id=uuid4(),
    indicator="Scope 1 GHG Emissions per tonne clinker",
    value=950.0,
    unit="kg CO₂/tonne",
    original_value=950.0,
    original_unit="kg CO₂/tonne"
)

# Validate
results = engine.validate_record(record, "cement_industry")
print(f"✅ Valid!" if not results else f"❌ {len(results)} issues found")
```

## 📊 Validation Rules

### Coverage

| Industry | Rules | Indicators Covered |
|----------|-------|-------------------|
| Cement | 3 | Emissions, Energy, Clinker Ratio |
| Steel | 3 | BF-BOF, EAF, Energy Intensity |
| Automotive | 3 | Manufacturing, VOC, Water |
| Cross-Industry | 8 | Scope, Temporal, Outliers, Units |
| Energy | 2 | Grid Factors, Renewables |
| Data Quality | 2 | Completeness, Precision |

### Validation Types

1. **Range Check** - Numeric bounds validation
2. **Category Check** - Enum/allowlist validation
3. **Outlier Detection** - Statistical z-score analysis
4. **Temporal Consistency** - Part-to-whole validation
5. **Pattern Match** - String format validation
6. **Null Check** - Required field validation
7. **Precision Check** - Decimal place validation

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/validate/upload` | POST | Validate entire upload |
| `/upload/{id}/errors` | GET | Get validation errors |
| `/upload/{id}/warnings` | GET | Get validation warnings |
| `/upload/{id}/report` | GET | Comprehensive report |
| `/upload/{id}/statistics` | GET | Validation statistics |
| `/validate/record` | POST | Validate single record |
| `/revalidate/record/{id}` | POST | Re-run validation |
| `/rules/summary` | GET | Rules summary |
| `/rules/industry/{name}` | GET | Industry rules |

## 📝 Example Responses

### Validation Summary
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
  }
}
```

### Validation Report
```json
{
  "upload_id": "uuid",
  "summary": { /* ValidationSummary */ },
  "errors": [ /* List of errors */ ],
  "warnings": [ /* List of warnings */ ],
  "recommendations": [
    "✅ Good! No errors found, only warnings.",
    "📏 Multiple values outside expected ranges detected.",
    "🔍 Most common error: 'cement_emission_range' (8 occurrences)."
  ]
}
```

## 🧪 Testing

```bash
# Run validation tests
pytest tests/test_validation.py -v

# Run service tests
pytest tests/test_validation_service.py -v

# Run with coverage
pytest tests/test_validation*.py --cov=src/validation --cov-report=html

# View coverage report
open htmlcov/index.html
```

## 📚 Documentation

- [Full Usage Guide](../docs/validation_usage.md)
- [API Documentation](http://localhost:8000/docs) (when server running)
- [Validation Rules Schema](../../data/validation-rules/validation_rules.json)

## 🔍 How It Works

### 1. Rule Loading
```python
engine = ValidationEngine(rules_path)
# Loads JSON rules → Parses into ValidationRule objects → Indexes by industry/indicator
```

### 2. Record Validation
```python
results = engine.validate_record(record, industry)
# Gets applicable rules → Executes each validation type → Returns failures only
```

### 3. Batch Processing
```python
results = engine.validate_batch(records, industry)
# Individual validations → Cross-record validations (outliers) → Aggregated results
```

### 4. Database Integration
```python
service.validate_upload(upload_id, industry)
# Fetch records → Run validations → Save to DB → Generate summary → Audit log
```

## 💡 Best Practices

1. **Always validate normalized data**, not raw input
2. **Use batch validation** for better performance
3. **Review warnings** even if no errors
4. **Update rules** when standards change
5. **Provide context** in error messages
6. **Cite sources** for all rules

## 🛠️ Adding Custom Rules

Edit `data/validation-rules/validation_rules.json`:

```json
{
  "your_industry": {
    "your_indicator": {
      "rule_name": "descriptive_name",
      "description": "What this validates",
      "indicator": "Specific indicator or empty",
      "validation_type": "range",
      "parameters": {"min": 0, "max": 100},
      "severity": "error",
      "citation": "Source reference",
      "error_message": "Clear message",
      "suggested_fixes": [
        "First suggestion",
        "Second suggestion"
      ]
    }
  }
}
```

## 📈 Performance

- **Batch validation**: ~1000 records/second
- **Database inserts**: Bulk operations for efficiency
- **Rule indexing**: O(1) lookup by industry/indicator
- **Outlier detection**: O(n) with statistics calculation

## 🤝 Integration Points

### With Ingestion Module
```python
# After parsing
parsed_data = parser.parse(file)
# Normalize
normalized_data = normalizer.normalize(parsed_data)
# Validate ✅
results = validator.validate(normalized_data)
```

### With Generation Module
```python
# Before generating reports
if validation_pass_rate >= 95:
    narrative = generator.generate_narrative(data)
else:
    raise ValidationError("Fix errors before generating reports")
```

## 🐛 Troubleshooting

### No Rules Loaded
```python
# Check path
assert Path(rules_path).exists()
```

### All Records Failing
```python
# Verify industry name matches rule structure
print(engine.rules.keys())  # Check available industries
```

### Outliers Not Detected
```python
# Need 3+ records for statistics
assert len(records) >= 3
```

## 📄 License

Part of AI ESG Reporting System - MIT License

## 👥 Contributors

Built for automated ESG data quality assurance with industry best practices.
