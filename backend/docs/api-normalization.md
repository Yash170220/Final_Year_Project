# Normalization API Documentation

## Overview
The Normalization API provides endpoints for converting ESG data to standardized units, retrieving normalized results, and managing normalization errors.

## Base URL
```
/api/v1/normalization
```

## Endpoints

### 1. Process Normalization

**POST** `/process/{upload_id}`

Trigger normalization for all approved matched indicators in an upload.

**Parameters:**
- `upload_id` (path, UUID): Upload identifier

**Response:** `200 OK`
```json
{
  "total_records": 2500,
  "successfully_normalized": 2450,
  "failed_normalization": 50,
  "unique_units_detected": ["kWh", "kg CO2e", "m3"],
  "conversions_applied": [
    {
      "conversion": "kWh→MWh",
      "count": 1500
    },
    {
      "conversion": "kg CO2e→tonnes CO2e",
      "count": 950
    }
  ],
  "errors": [
    "Error processing Water Usage: Could not detect unit"
  ]
}
```

**Error Responses:**
- `400 Bad Request`: Upload not found or no approved indicators
- `500 Internal Server Error`: Normalization processing failed

**Example:**
```bash
curl -X POST "http://localhost:8000/api/v1/normalization/process/123e4567-e89b-12d3-a456-426614174000"
```

---

### 2. Get Normalization Results

**GET** `/results/{upload_id}`

Retrieve all normalized data for an upload, grouped by indicator.

**Parameters:**
- `upload_id` (path, UUID): Upload identifier
- `indicator_name` (query, optional): Filter by canonical indicator name

**Response:** `200 OK`
```json
{
  "upload_id": "123e4567-e89b-12d3-a456-426614174000",
  "indicators": [
    {
      "indicator": "Energy Consumption",
      "records": [
        {
          "row_index": 0,
          "original_value": 5000,
          "original_unit": "kWh",
          "normalized_value": 5.0,
          "normalized_unit": "MWh"
        },
        {
          "row_index": 1,
          "original_value": 6000,
          "original_unit": "kWh",
          "normalized_value": 6.0,
          "normalized_unit": "MWh"
        }
      ]
    },
    {
      "indicator": "CO2 Emissions",
      "records": [
        {
          "row_index": 0,
          "original_value": 2500,
          "original_unit": "kg CO2e",
          "normalized_value": 2.5,
          "normalized_unit": "tonnes CO2e"
        }
      ]
    }
  ],
  "total_records": 3
}
```

**Example:**
```bash
# Get all results
curl "http://localhost:8000/api/v1/normalization/results/123e4567-e89b-12d3-a456-426614174000"

# Filter by indicator
curl "http://localhost:8000/api/v1/normalization/results/123e4567-e89b-12d3-a456-426614174000?indicator_name=Energy%20Consumption"
```

---

### 3. Get Conversions

**GET** `/conversions/{upload_id}`

Get detailed information about all unit conversions applied.

**Parameters:**
- `upload_id` (path, UUID): Upload identifier

**Response:** `200 OK`
```json
{
  "upload_id": "123e4567-e89b-12d3-a456-426614174000",
  "conversions": [
    {
      "indicator": "Energy Consumption",
      "original_unit": "kWh",
      "normalized_unit": "MWh",
      "conversion_factor": 0.001,
      "source": "SI standard",
      "formula": "kWh * 0.001 = MWh",
      "record_count": 1500
    },
    {
      "indicator": "CO2 Emissions",
      "original_unit": "kg CO2e",
      "normalized_unit": "tonnes CO2e",
      "conversion_factor": 0.001,
      "source": "GHG Protocol",
      "formula": "kg CO2e * 0.001 = tonnes CO2e",
      "record_count": 950
    }
  ]
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/normalization/conversions/123e4567-e89b-12d3-a456-426614174000"
```

---

### 4. Get Normalization Errors

**GET** `/errors/{upload_id}`

Retrieve normalization errors and suggestions for manual review.

**Parameters:**
- `upload_id` (path, UUID): Upload identifier

**Response:** `200 OK`
```json
{
  "upload_id": "123e4567-e89b-12d3-a456-426614174000",
  "error_count": 2,
  "errors": [
    {
      "indicator": "Water Usage",
      "issue": "No normalized data",
      "details": "Header: Water Consumption",
      "suggestion": "Unit could not be detected. Specify unit in header or review manually"
    },
    {
      "indicator": "Energy Consumption",
      "issue": "Conflicting units detected",
      "details": "Multiple units found: kWh, MWh",
      "suggestion": "Review data source and ensure consistent units"
    }
  ]
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/normalization/errors/123e4567-e89b-12d3-a456-426614174000"
```

---

### 5. Get Normalization Summary

**GET** `/summary/{upload_id}`

Get comprehensive normalization statistics.

**Parameters:**
- `upload_id` (path, UUID): Upload identifier

**Response:** `200 OK`
```json
{
  "upload_id": "123e4567-e89b-12d3-a456-426614174000",
  "total_indicators": 5,
  "total_normalized_records": 2450,
  "unique_units": ["kWh", "kg CO2e", "m3", "tonnes"],
  "conversions": [
    {
      "conversion": "kWh→MWh",
      "count": 1500
    },
    {
      "conversion": "kg CO2e→tonnes CO2e",
      "count": 950
    }
  ]
}
```

**Example:**
```bash
curl "http://localhost:8000/api/v1/normalization/summary/123e4567-e89b-12d3-a456-426614174000"
```

---

## Workflow Example

### Complete Normalization Workflow

```bash
# 1. Upload file
UPLOAD_ID=$(curl -X POST "http://localhost:8000/api/v1/ingestion/upload" \
  -F "file=@facility_data.xlsx" \
  | jq -r '.upload_id')

# 2. Process matching
curl -X POST "http://localhost:8000/api/v1/matching/process/${UPLOAD_ID}"

# 3. Review and approve matches
curl -X POST "http://localhost:8000/api/v1/matching/review" \
  -H "Content-Type: application/json" \
  -d '{
    "upload_id": "'${UPLOAD_ID}'",
    "reviews": [
      {
        "matched_header": "Electricity (kWh)",
        "approved": true
      }
    ]
  }'

# 4. Process normalization
curl -X POST "http://localhost:8000/api/v1/normalization/process/${UPLOAD_ID}"

# 5. Get results
curl "http://localhost:8000/api/v1/normalization/results/${UPLOAD_ID}"

# 6. Check for errors
curl "http://localhost:8000/api/v1/normalization/errors/${UPLOAD_ID}"

# 7. Get conversion details
curl "http://localhost:8000/api/v1/normalization/conversions/${UPLOAD_ID}"
```

---

## Error Handling

### Common Error Codes

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request - Upload not found or invalid parameters |
| 404 | Not Found - Resource does not exist |
| 500 | Internal Server Error - Processing failed |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

---

## Data Models

### NormalizationSummary
```typescript
{
  total_records: number;
  successfully_normalized: number;
  failed_normalization: number;
  unique_units_detected: string[];
  conversions_applied: Array<{
    conversion: string;
    count: number;
  }>;
  errors: string[];
}
```

### NormalizedRecord
```typescript
{
  row_index: number;
  original_value: number;
  original_unit: string;
  normalized_value: number;
  normalized_unit: string;
}
```

### ConversionInfo
```typescript
{
  indicator: string;
  original_unit: string;
  normalized_unit: string;
  conversion_factor: number;
  source: string;
  formula: string;
  record_count: number;
}
```

### ErrorInfo
```typescript
{
  indicator: string;
  issue: string;
  details: string;
  suggestion: string;
}
```

---

## Best Practices

1. **Always check errors after normalization**
   ```bash
   curl "http://localhost:8000/api/v1/normalization/errors/${UPLOAD_ID}"
   ```

2. **Review conversions for accuracy**
   - Verify conversion factors match expected standards
   - Check source citations for regulatory compliance

3. **Handle missing units proactively**
   - Include units in column headers: "Energy (kWh)"
   - Use standard unit abbreviations

4. **Monitor normalization statistics**
   - Track success rates across uploads
   - Identify patterns in failed normalizations

5. **Validate results before downstream processing**
   - Compare original vs normalized values
   - Spot-check conversion calculations

---

## Rate Limits

No rate limits currently enforced. For production deployments, consider:
- Max 100 requests per minute per IP
- Max 10 concurrent normalization processes

---

## Support

For issues or questions:
- Check error messages in `/errors/{upload_id}` endpoint
- Review conversion factors in `data/validation-rules/conversion_factors.json`
- Consult unit normalizer documentation
