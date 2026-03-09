# ESG Report Templates

## Status: Manual Creation Required

This directory should contain the following template files:

1. **brsr_template.docx** - BRSR (Business Responsibility and Sustainability Reporting) template
2. **gri_template.docx** - GRI (Global Reporting Initiative) Standards template

## Why Manual Creation?

These templates require:
- Proper document formatting (headers, footers, page breaks)
- Complex table structures
- Logo placeholders
- Specific styling per reporting standards
- Compliance with official formats

Automated generation would not maintain the required formatting fidelity.

## How to Create Templates

Follow the detailed instructions in:
- `TEMPLATE_CREATION_INSTRUCTIONS.md` - Step-by-step guide
- `BRSR_TEMPLATE_STRUCTURE.md` - BRSR structure and placeholders
- `GRI_TEMPLATE_STRUCTURE.md` - GRI structure and placeholders

## Quick Start

### BRSR Template
1. Download official format from SEBI: https://www.sebi.gov.in/
2. Create Word document with sections A, B, C, D
3. Insert placeholders: `{{COMPANY_NAME}}`, `{{ENERGY_TOTAL_MWH}}`, etc.
4. Save as `brsr_template.docx`

### GRI Template
1. Download GRI Standards from: https://www.globalreporting.org/standards/
2. Create Word document with GRI 2, 302, 303, 305, 306 sections
3. Insert placeholders: `{{ENERGY_TOTAL_GJ}}`, `{{GHG_SCOPE1_TONNES}}`, etc.
4. Save as `gri_template.docx`

## Placeholder Format

All placeholders use double curly braces:
```
{{PLACEHOLDER_NAME}}
```

Examples:
- `{{COMPANY_NAME}}` - Company name
- `{{ENERGY_TOTAL_MWH}}` - Total energy in MWh
- `{{GHG_SCOPE1_TONNES}}` - Scope 1 emissions in tonnes CO₂e
- `{{WATER_TOTAL_M3}}` - Total water consumption in m³

## Data Mapping

The system will automatically map normalized data to placeholders:

```python
# Example mapping
normalized_data["Total Electricity Consumption"] → {{ENERGY_TOTAL_MWH}}
normalized_data["Scope 1 Emissions"] → {{GHG_SCOPE1_TONNES}}
normalized_data["Total Water Consumption"] → {{WATER_TOTAL_M3}}
```

## File Structure

```
data/templates/
├── README.md (this file)
├── TEMPLATE_CREATION_INSTRUCTIONS.md
├── BRSR_TEMPLATE_STRUCTURE.md
├── GRI_TEMPLATE_STRUCTURE.md
├── brsr_template.docx (TO BE CREATED)
└── gri_template.docx (TO BE CREATED)
```

## Validation

After creating templates:
1. Open in Microsoft Word
2. Use Find & Replace to search for `{{`
3. Verify all placeholders are correctly formatted
4. Test with sample data
5. Check formatting remains intact

## Integration

Once templates are created, the report generation service will:
1. Load template file using `python-docx`
2. Fetch normalized data from database
3. Apply unit conversions if needed
4. Replace all placeholders with actual values
5. Generate final report as PDF/DOCX

## Support

- BRSR: https://www.sebi.gov.in/
- GRI: https://www.globalreporting.org/
- Template issues: Check structure documentation
