# Validation API Endpoints - Prompt 28 Implementation

## ✅ Completed Endpoints

### 1. POST `/api/v1/validation/process/{upload_id}`
**Trigger validation for normalized data**

**Parameters:**
- `upload_id` (path): UUID of the upload
- `industry` (query): Industry category (cement_industry, steel_industry, automotive_industry)

**Example Request:**
```bash
POST /api/v1/validation/process/123e4567-e89b-12d3-a456-426614174000?industry=cement_industry
```

**Response:**
```json
{
  "total_records": 1500,
  "valid_records": 1420,
  "records_with_errors": 50,
  "records_with_warnings": 30,
  "validation_pass_rate": 94.67,
  "error_breakdown": {
    "cement_emission_range": 45,
    "detect_decimal_errors": 5
  },
  "warning_breakdown": {
    "cement_energy_range": 30
  }
}
```

---

### 2. GET `/api/v1/validation/errors/{upload_id}`
**Get all validation errors with suggested fixes**

**Parameters:**
- `upload_id` (path): UUID of the upload

**Example Request:**
```bash
GET /api/v1/validation/errors/123e4567-e89b-12d3-a456-426614174000
```

**Response:**
```json
{
  "upload_id": "123e4567-e89b-12d3-a456-426614174000",
  "total_errors": 50,
  "errors": [
    {
      "data_id": "uuid",
      "indicator": "cement_emission_range",
      "rule": "cement_emission_range",
      "severity": "error",
      "message": "Value 15000 kg CO₂/tonne outside range (800-1100)",
      "suggested_fixes": [
        "Check if value should be in tonnes instead of kg (divide by 1000)",
        "Verify clinker ratio is calculated correctly",
        "Review fuel mix and process efficiency data"
      ],
      "citation": "Andrew (2019) - Global CO₂ emissions from cement production",
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

---

### 3. GET `/api/v1/validation/warnings/{upload_id}`
**Get all validation warnings (less critical)**

**Parameters:**
- `upload_id` (path): UUID of the upload

**Example Request:**
```bash
GET /api/v1/validation/warnings/123e4567-e89b-12d3-a456-426614174000
```

**Response:**
```json
{
  "upload_id": "123e4567-e89b-12d3-a456-426614174000",
  "total_warnings": 30,
  "warnings": [
    {
      "data_id": "uuid",
      "indicator": "cement_energy_range",
      "rule": "cement_energy_range",
      "severity": "warning",
      "message": "Energy intensity 4.4 GJ/tonne at upper bound of typical range",
      "suggested_fixes": [
        "Verify thermal and electrical energy are both included",
        "Check if pre-heating and grinding energy is accounted for",
        "Review kiln efficiency metrics"
      ],
      "citation": "IEA Technology Roadmap - Low-Carbon Transition in the Cement Industry",
      "created_at": "2024-01-15T10:30:00"
    }
  ]
}
```

---

### 4. GET `/api/v1/validation/report/{upload_id}`
**Generate comprehensive validation report with charts data**

**Parameters:**
- `upload_id` (path): UUID of the upload

**Example Request:**
```bash
GET /api/v1/validation/report/123e4567-e89b-12d3-a456-426614174000
```

**Response (matches exact format from Prompt 28):**
```json
{
  "upload_id": "123e4567-e89b-12d3-a456-426614174000",
  "summary": {
    "total_records": 1500,
    "valid_records": 1420,
    "records_with_errors": 50,
    "records_with_warnings": 30,
    "validation_pass_rate": 94.67
  },
  "errors": [
    {
      "indicator": "Scope 1 Emissions",
      "rule": "cement_emission_range",
      "severity": "error",
      "message": "Value 15000 kg CO₂/tonne outside range (800-1100)",
      "suggested_fix": "Likely unit error - divide by 10 (should be 1500 kg CO₂/tonne)",
      "citation": "Andrew (2019)"
    }
  ],
  "warnings": [
    {
      "indicator": "Energy Intensity",
      "rule": "cement_energy_range",
      "severity": "warning",
      "message": "Energy intensity at upper bound",
      "suggested_fix": "Review kiln efficiency metrics",
      "citation": "IEA Technology Roadmap"
    }
  ],
  "recommendations": [
    "Review 50 records flagged with emission range errors",
    "Consider updating clinker ratio calculation for Plant B",
    "30 warnings about minor temporal inconsistencies - acceptable variance"
  ],
  "charts_data": {
    "error_distribution": {
      "cement_emission_range": 45,
      "detect_decimal_errors": 5
    },
    "warning_distribution": {
      "cement_energy_range": 30
    },
    "pass_rate": {
      "passed": 1450,
      "failed": 50
    },
    "severity_breakdown": {
      "errors": 50,
      "warnings": 30,
      "valid": 1420
    }
  },
  "generated_at": "2024-01-15T10:30:00"
}
```

---

### 5. GET `/api/v1/validation/rules`
**List all available validation rules (filterable by industry)**

**Parameters:**
- `industry` (query, optional): Filter by industry (cement_industry, steel_industry, etc.)

**Example Requests:**
```bash
# Get all rules
GET /api/v1/validation/rules

# Filter by industry
GET /api/v1/validation/rules?industry=cement_industry
```

**Response:**
```json
{
  "total_rules": 20,
  "industries": ["cement_industry", "steel_industry", "automotive_industry", "cross_industry"],
  "filtered_by": "all",
  "rules": [
    {
      "rule_name": "cement_emission_range",
      "industry": "cement_industry",
      "description": "Cement production emissions typically 800-1,100 kg CO₂/tonne clinker",
      "indicator": "Scope 1 GHG Emissions per tonne clinker",
      "validation_type": "range",
      "severity": "error",
      "parameters": {
        "min": 800,
        "max": 1100,
        "unit": "kg CO₂/tonne"
      },
      "citation": "Andrew (2019) - Global CO₂ emissions from cement production",
      "error_message": "Cement emissions outside typical range. Possible unit error or data entry mistake.",
      "suggested_fixes": [
        "Check if value should be in tonnes instead of kg (divide by 1000)",
        "Verify clinker ratio is calculated correctly",
        "Review fuel mix and process efficiency data"
      ]
    }
  ]
}
```

---

## 📊 Response Format Compliance

All endpoints match the exact format specified in Prompt 28:

✅ **Summary Structure:**
- `total_records`: int
- `valid_records`: int  
- `records_with_errors`: int
- `records_with_warnings`: int
- `validation_pass_rate`: float (percentage)

✅ **Error/Warning Structure:**
- `indicator`: string
- `rule`: string
- `severity`: "error" | "warning"
- `message`: string
- `suggested_fix`: string (or `suggested_fixes`: array)
- `citation`: string

✅ **Recommendations:**
- Array of actionable recommendation strings

✅ **Charts Data:**
- `error_distribution`: Object mapping rule names to counts
- `warning_distribution`: Object mapping rule names to counts
- `pass_rate`: Pass/fail breakdown
- `severity_breakdown`: Error/warning/valid counts

---

## 🚀 Usage Examples

### Complete Validation Workflow

```bash
# 1. Trigger validation
curl -X POST "http://localhost:8000/api/v1/validation/process/upload-uuid?industry=cement_industry"

# 2. Get comprehensive report
curl -X GET "http://localhost:8000/api/v1/validation/report/upload-uuid"

# 3. Review errors only
curl -X GET "http://localhost:8000/api/v1/validation/errors/upload-uuid"

# 4. Review warnings
curl -X GET "http://localhost:8000/api/v1/validation/warnings/upload-uuid"

# 5. Check available rules
curl -X GET "http://localhost:8000/api/v1/validation/rules?industry=cement_industry"
```

### Python Client Example

```python
import requests

BASE_URL = "http://localhost:8000/api/v1/validation"

# Trigger validation
response = requests.post(
    f"{BASE_URL}/process/{upload_id}",
    params={"industry": "cement_industry"}
)
summary = response.json()
print(f"Pass rate: {summary['validation_pass_rate']}%")

# Get full report
report = requests.get(f"{BASE_URL}/report/{upload_id}").json()

# Display recommendations
for rec in report["recommendations"]:
    print(f"💡 {rec}")

# Review errors
errors = requests.get(f"{BASE_URL}/errors/{upload_id}").json()
for error in errors["errors"]:
    print(f"❌ {error['rule']}: {error['message']}")
    print(f"   Fix: {error['suggested_fixes'][0]}")
```

---

## 📝 Additional Utility Endpoints

### GET `/api/v1/validation/health`
Health check for validation engine

### GET `/api/v1/validation/rules/summary`
Quick summary of rules (total count, industries, types)

### GET `/api/v1/validation/upload/{upload_id}/statistics`
Detailed validation statistics

### POST `/api/v1/validation/revalidate/record/{data_id}`
Re-run validation for a single record

---

## 🎯 Key Features Implemented

1. ✅ **Exact Response Format** - Matches Prompt 28 specification exactly
2. ✅ **Suggested Fixes** - All errors/warnings include actionable suggestions
3. ✅ **Citations** - Every rule includes authoritative source reference
4. ✅ **Charts Data** - Ready for visualization in frontend
5. ✅ **Industry Filtering** - Rules endpoint filterable by industry
6. ✅ **Comprehensive Reports** - Full report with recommendations
7. ✅ **Error Handling** - Graceful failures with helpful messages
8. ✅ **Documentation** - Clear examples and descriptions

---

## 🔗 Integration Points

### Frontend Integration
```javascript
// Fetch validation report
const report = await fetch(`/api/v1/validation/report/${uploadId}`)
  .then(r => r.json());

// Display error chart
const errorChart = report.charts_data.error_distribution;
// Use with Chart.js, D3, etc.

// Show recommendations
report.recommendations.forEach(rec => {
  displayRecommendation(rec);
});
```

### Backend Pipeline
```python
# After normalization
summary = await validation_service.validate_upload(upload_id, industry)

if summary.validation_pass_rate < 95:
    # Review required
    return {"status": "needs_review", "errors": summary.records_with_errors}
else:
    # Proceed to report generation
    proceed_to_generation(upload_id)
```

---

## ✅ Prompt 28 Completion Checklist

- ✅ POST `/process/{upload_id}` - Trigger validation
- ✅ GET `/errors/{upload_id}` - Get errors with fixes
- ✅ GET `/warnings/{upload_id}` - Get warnings  
- ✅ GET `/report/{upload_id}` - Comprehensive report with charts
- ✅ GET `/rules` - List rules (filterable)
- ✅ Response format matches specification exactly
- ✅ Suggested fixes included in all responses
- ✅ Citations included for all rules
- ✅ Recommendations generated intelligently
- ✅ Charts data prepared for visualization

**All requirements from Prompt 28 completed!** 🎉
