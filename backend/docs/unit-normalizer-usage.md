# Unit Normalizer - Usage Examples

## Overview
The `UnitNormalizer` converts ESG data values from various units to standardized base units using a comprehensive conversion factor database.

## Quick Start

```python
from src.normalization import UnitNormalizer

# Initialize normalizer
normalizer = UnitNormalizer("data/validation-rules/conversion_factors.json")

# Normalize a value
result = normalizer.normalize(5000, "kWh", "energy")
print(f"{result.original_value} {result.original_unit} = "
      f"{result.normalized_value} {result.normalized_unit}")
# Output: 5000 kWh = 5.0 MWh
```

## Core Features

### 1. Unit Normalization

Convert values to base units:

```python
# Energy conversions
result = normalizer.normalize(5000, "kWh", "energy")
# 5000 kWh -> 5.0 MWh

result = normalizer.normalize(100, "GJ", "energy")
# 100 GJ -> 27.7778 MWh

result = normalizer.normalize(1000000, "BTU", "energy")
# 1000000 BTU -> 293.071 MWh

# Mass conversions
result = normalizer.normalize(1500, "kg", "mass")
# 1500 kg -> 1.5 tonnes

result = normalizer.normalize(2204.62, "pounds", "mass")
# 2204.62 pounds -> 1.0 tonnes

# Emissions conversions
result = normalizer.normalize(2500, "kg CO₂e", "emissions")
# 2500 kg CO₂e -> 2.5 tonnes CO₂e

# Compound unit conversions
result = normalizer.normalize(0.5, "kWh/kg", "compound_energy_intensity")
# 0.5 kWh/kg -> 0.5 MWh/tonne
```

### 2. Automatic Category Detection

Omit category parameter for automatic detection:

```python
result = normalizer.normalize(5000, "kWh")
# Automatically detects "energy" category
# 5000 kWh -> 5.0 MWh
```

### 3. Unit Detection from Text

Extract units from text strings:

```python
unit, category = normalizer.detect_unit("5000 kWh")
# Returns: ("kWh", "energy")

unit, category = normalizer.detect_unit("12.5 tonnes CO₂e")
# Returns: ("tonnes CO₂e", "emissions")

unit, category = normalizer.detect_unit("Energy consumption: 1500kg")
# Returns: ("kg", "mass")
```

### 4. Conversion Factor Lookup

Get conversion factors between any two units:

```python
factor = normalizer.get_conversion_factor("kWh", "MWh")
print(f"Factor: {factor.factor}")
print(f"Source: {factor.source}")
print(f"Formula: {factor.formula}")
# Factor: 0.001
# Source: SI standard, Base unit
# Formula: kWh * 0.001 = MWh

# Reverse conversion
factor = normalizer.get_conversion_factor("MWh", "kWh")
# Factor: 1000.0
```

### 5. Conversion Validation

Check if conversion is valid before attempting:

```python
# Valid conversion (same category)
is_valid = normalizer.validate_conversion("kWh", "MWh")
# Returns: True

# Invalid conversion (different categories)
is_valid = normalizer.validate_conversion("kWh", "kg")
# Returns: False

# Unknown unit
is_valid = normalizer.validate_conversion("xyz", "MWh")
# Returns: False
```

### 6. Utility Methods

```python
# Get base unit for a category
base_unit = normalizer.get_base_unit("energy")
# Returns: "MWh"

# Get all supported units
all_units = normalizer.get_supported_units()
# Returns: {"energy": ["MWh", "kWh", "GJ", ...], "mass": [...], ...}

# Get supported units for specific category
energy_units = normalizer.get_supported_units("energy")
# Returns: {"energy": ["MWh", "kWh", "GJ", "MJ", "TJ", "BTU", ...]}
```

## Normalization Result

The `normalize()` method returns a `NormalizationResult` object:

```python
result = normalizer.normalize(5000, "kWh", "energy")

print(result.original_value)      # 5000
print(result.original_unit)       # "kWh"
print(result.normalized_value)    # 5.0
print(result.normalized_unit)     # "MWh"
print(result.conversion_factor)   # 0.001
print(result.conversion_source)   # "SI standard"
print(result.formula)             # "kWh * 0.001 = MWh"
```

## Error Handling

### UnitNotFoundError

Raised when a unit is not in the database:

```python
try:
    normalizer.normalize(100, "xyz", "energy")
except UnitNotFoundError as e:
    print(f"Error: {e}")
    # Error: Unit 'xyz' not found in category 'energy'
```

### CategoryMismatchError

Raised when converting between incompatible categories:

```python
try:
    normalizer.get_conversion_factor("kWh", "kg")
except CategoryMismatchError as e:
    print(f"Error: {e}")
    # Error: Cannot convert between different categories: kWh (energy) to kg (mass)
```

### InvalidValueError

Raised for invalid values:

```python
try:
    normalizer.normalize(-100, "kWh", "energy")
except InvalidValueError as e:
    print(f"Error: {e}")
    # Error: Negative value for absolute measure: -100 kWh
```

## Supported Unit Categories

### Simple Units
- **Energy**: MWh (base), kWh, GWh, GJ, MJ, TJ, BTU, MMBTU, therm, kcal, Mcal, kJ, Wh
- **Mass**: tonnes (base), kg, g, mg, pounds, lbs, short_tons, long_tons, metric_tons, ounces
- **Volume**: m³ (base), liters, L, mL, gallons, cubic_feet, cubic_inches, barrels
- **Emissions**: tonnes CO₂e (base), kg CO₂e, g CO₂e, pounds CO₂e, metric tons CO₂e, short tons CO₂e, Mt CO₂e
- **Area**: m² (base), km², hectares, acres, square_feet
- **Power**: MW (base), kW, W, GW, hp
- **Pressure**: bar (base), Pa, kPa, MPa, psi, atm

### Compound Units
- **Energy Intensity**: MWh/tonne (base), kWh/kg, GJ/tonne, MJ/kg, BTU/lb, kWh/tonne
- **Emission Intensity**: kg CO₂e/MWh (base), tonnes CO₂e/MWh, g CO₂e/kWh, kg CO₂e/GJ, pounds CO₂e/MMBTU
- **Water Intensity**: m³/tonne (base), L/kg, gallons/ton, m³/kg
- **Waste Intensity**: kg/tonne (base), tonnes/tonne, g/kg, pounds/ton

## Integration Example

```python
from src.normalization import UnitNormalizer
import polars as pl

# Initialize normalizer
normalizer = UnitNormalizer("data/validation-rules/conversion_factors.json")

# Sample ESG data
data = pl.DataFrame({
    "indicator": ["Energy Consumption", "CO2 Emissions", "Water Usage"],
    "value": [5000, 2500, 1000],
    "unit": ["kWh", "kg CO₂e", "liters"]
})

# Normalize all values
normalized_values = []
normalized_units = []

for row in data.iter_rows(named=True):
    result = normalizer.normalize(row["value"], row["unit"])
    normalized_values.append(result.normalized_value)
    normalized_units.append(result.normalized_unit)

# Add normalized columns
data = data.with_columns([
    pl.Series("normalized_value", normalized_values),
    pl.Series("normalized_unit", normalized_units)
])

print(data)
# ┌─────────────────────┬───────┬───────────┬──────────────────┬─────────────────┐
# │ indicator           │ value │ unit      │ normalized_value │ normalized_unit │
# ├─────────────────────┼───────┼───────────┼──────────────────┼─────────────────┤
# │ Energy Consumption  │ 5000  │ kWh       │ 5.0              │ MWh             │
# │ CO2 Emissions       │ 2500  │ kg CO₂e   │ 2.5              │ tonnes CO₂e     │
# │ Water Usage         │ 1000  │ liters    │ 1.0              │ m³              │
# └─────────────────────┴───────┴───────────┴──────────────────┴─────────────────┘
```

## Best Practices

1. **Initialize Once**: Create a single `UnitNormalizer` instance and reuse it
2. **Validate First**: Use `validate_conversion()` before batch operations
3. **Handle Errors**: Always wrap normalization in try-except blocks
4. **Use Auto-Detection**: Omit category parameter when possible for cleaner code
5. **Cache Results**: Store `NormalizationResult` objects for audit trails
6. **Check Sources**: Review `conversion_source` for regulatory compliance

## Performance Notes

- Unit lookup: O(1) using dictionary
- Conversion: O(1) arithmetic operation
- Detection: O(n) where n = number of units (optimized with longest-first matching)
- Thread-safe: Can be used in concurrent environments
