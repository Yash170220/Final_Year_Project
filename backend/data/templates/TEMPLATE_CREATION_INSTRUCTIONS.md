# Template Creation Instructions

## Overview
This document provides step-by-step instructions for creating the BRSR and GRI report templates manually.

## Prerequisites
- Microsoft Word or LibreOffice Writer
- Access to official BRSR and GRI documentation
- Understanding of sustainability reporting requirements

---

## STEP 1: Create BRSR Template

### 1.1 Download Official BRSR Format

**Source:** SEBI (Securities and Exchange Board of India)

**URL:** https://www.sebi.gov.in/legal/circulars/jul-2023/business-responsibility-and-sustainability-reporting-by-listed-entities_73592.html

**Steps:**
1. Visit the SEBI website
2. Download the official BRSR Core format (PDF/Word)
3. Review the structure and requirements

### 1.2 Create Template Document

**File:** `data/templates/brsr_template.docx`

**Structure:**
1. Open Microsoft Word
2. Set page size to A4
3. Set margins to 1 inch on all sides
4. Use Arial font (11pt body, 12pt headings)

### 1.3 Add Sections

Create the following sections in order:

#### Cover Page
- Company logo placeholder
- Report title
- Financial year
- Company name and CIN

#### Section A: General Disclosures
- Company details
- Products/Services
- Operations
- Employees
- Holding/Subsidiary companies
- CSR details

#### Section B: Management and Process Disclosures
- Policy frameworks
- Board oversight
- Stakeholder engagement

#### Section C: Principle-wise Performance
- Principle 1: Ethics
- Principle 2: Product Lifecycle
- Principle 3: Employee Well-being
- Principle 4: Stakeholder Engagement
- Principle 5: Human Rights
- Principle 6: Environment (KEY SECTION)
- Principle 7: Policy Advocacy
- Principle 8: Inclusive Growth
- Principle 9: Customer Value

#### Section D: Additional Disclosures

### 1.4 Insert Placeholders

Replace all data fields with placeholders in the format `{{PLACEHOLDER_NAME}}`:

**Example:**
```
Company Name: {{COMPANY_NAME}}
CIN: {{CIN}}
Total Energy Consumption: {{ENERGY_TOTAL_MWH}} MWh
Scope 1 Emissions: {{GHG_SCOPE1_TONNES}} tonnes CO₂e
```

**Key Environmental Placeholders:**
- `{{ENERGY_TOTAL_MWH}}`
- `{{ENERGY_RENEWABLE_MWH}}`
- `{{ENERGY_INTENSITY}}`
- `{{GHG_SCOPE1_TONNES}}`
- `{{GHG_SCOPE2_TONNES}}`
- `{{GHG_SCOPE3_TONNES}}`
- `{{GHG_TOTAL_TONNES}}`
- `{{GHG_INTENSITY}}`
- `{{WATER_TOTAL_M3}}`
- `{{WATER_RECYCLED_M3}}`
- `{{WATER_INTENSITY}}`
- `{{WASTE_TOTAL_TONNES}}`
- `{{WASTE_HAZARDOUS_TONNES}}`
- `{{WASTE_RECYCLED_TONNES}}`

### 1.5 Format Tables

Create tables for data presentation:
- Use bordered tables
- Header row with gray background
- Align numbers to the right
- Include units in column headers

### 1.6 Save Template

Save as: `data/templates/brsr_template.docx`

---

## STEP 2: Create GRI Template

### 2.1 Download GRI Standards

**Source:** Global Reporting Initiative

**URL:** https://www.globalreporting.org/standards/

**Key Standards to Download:**
- GRI 2: General Disclosures (2021)
- GRI 302: Energy (2016)
- GRI 303: Water and Effluents (2018)
- GRI 305: Emissions (2016)
- GRI 306: Waste (2020)

### 2.2 Create Template Document

**File:** `data/templates/gri_template.docx`

**Structure:**
1. Open Microsoft Word
2. Set page size to A4
3. Set margins to 1 inch on all sides
4. Use Arial font (10pt body, 14pt headings)

### 2.3 Add Sections

#### Cover Page
- Report title: "Sustainability Report [Year]"
- Company logo
- Reporting period
- Publication date
- Contact information

#### Table of Contents
- Auto-generated with page numbers

#### GRI 2: General Disclosures
- 2-1 to 2-30 (all disclosures)

#### GRI 302: Energy
- 302-1: Energy consumption within organization
- 302-2: Energy consumption outside organization
- 302-3: Energy intensity
- 302-4: Reduction of energy consumption
- 302-5: Reductions in energy requirements

#### GRI 303: Water and Effluents
- 303-1: Interactions with water
- 303-2: Management of water discharge
- 303-3: Water withdrawal
- 303-4: Water discharge
- 303-5: Water consumption

#### GRI 305: Emissions
- 305-1: Direct (Scope 1) GHG emissions
- 305-2: Energy indirect (Scope 2) GHG emissions
- 305-3: Other indirect (Scope 3) GHG emissions
- 305-4: GHG emissions intensity
- 305-5: Reduction of GHG emissions
- 305-6: Emissions of ozone-depleting substances
- 305-7: NOx, SOx, and other air emissions

#### GRI 306: Waste
- 306-1: Waste generation and impacts
- 306-2: Management of waste impacts
- 306-3: Waste generated
- 306-4: Waste diverted from disposal
- 306-5: Waste directed to disposal

#### GRI Content Index
- Table mapping all disclosures to page numbers

### 2.4 Insert Placeholders

**Energy Placeholders (GRI 302):**
- `{{ENERGY_TOTAL_GJ}}`
- `{{ENERGY_TOTAL_MWH}}`
- `{{ENERGY_FUEL_CONSUMPTION_GJ}}`
- `{{ENERGY_ELECTRICITY_PURCHASED_GJ}}`
- `{{ENERGY_INTENSITY_RATIO}}`
- `{{ENERGY_REDUCTION_GJ}}`

**Emissions Placeholders (GRI 305):**
- `{{GHG_SCOPE1_TONNES}}`
- `{{GHG_SCOPE2_LOCATION_TONNES}}`
- `{{GHG_SCOPE2_MARKET_TONNES}}`
- `{{GHG_SCOPE3_TONNES}}`
- `{{GHG_INTENSITY_RATIO}}`
- `{{GHG_REDUCTION_TONNES}}`
- `{{NOX_EMISSIONS_TONNES}}`
- `{{SOX_EMISSIONS_TONNES}}`
- `{{PM_EMISSIONS_TONNES}}`

**Water Placeholders (GRI 303):**
- `{{WATER_WITHDRAWAL_TOTAL_ML}}`
- `{{WATER_DISCHARGE_TOTAL_ML}}`
- `{{WATER_CONSUMPTION_TOTAL_ML}}`
- `{{WATER_STRESS_AREAS}}`

**Waste Placeholders (GRI 306):**
- `{{WASTE_TOTAL_TONNES}}`
- `{{WASTE_HAZARDOUS_TONNES}}`
- `{{WASTE_NON_HAZARDOUS_TONNES}}`
- `{{WASTE_RECYCLING_TONNES}}`
- `{{WASTE_LANDFILL_TONNES}}`

### 2.5 Format Tables

Use GRI-compliant table format:
```
| Disclosure | Value | Unit | Notes |
|------------|-------|------|-------|
| 302-1 | {{ENERGY_TOTAL_GJ}} | GJ | Total energy |
```

### 2.6 Save Template

Save as: `data/templates/gri_template.docx`

---

## STEP 3: Validation

### 3.1 Check Placeholders

Verify all placeholders:
1. Use Find & Replace to search for `{{`
2. Ensure all placeholders follow naming convention
3. Check for typos in placeholder names

### 3.2 Test Template

1. Create a copy of the template
2. Replace a few placeholders with sample data
3. Verify formatting remains intact
4. Check page breaks and table layouts

### 3.3 Document Mapping

Create a mapping document showing:
- Which normalized data fields map to which placeholders
- Unit conversions required (e.g., MWh to GJ)
- Calculation formulas for derived metrics

---

## STEP 4: Integration with System

### 4.1 Template Location

Ensure templates are saved in:
```
backend/data/templates/
├── brsr_template.docx
└── gri_template.docx
```

### 4.2 Placeholder Mapping

Create mapping configuration:
```python
BRSR_MAPPING = {
    "Total Electricity Consumption": "{{ENERGY_TOTAL_MWH}}",
    "Scope 1 Emissions": "{{GHG_SCOPE1_TONNES}}",
    # ... more mappings
}

GRI_MAPPING = {
    "Total Electricity Consumption": {
        "placeholder": "{{ENERGY_TOTAL_GJ}}",
        "conversion": lambda x: x * 3.6  # MWh to GJ
    },
    # ... more mappings
}
```

### 4.3 Report Generation Service

The system will:
1. Load template file
2. Fetch normalized data from database
3. Apply unit conversions
4. Replace placeholders with actual values
5. Generate final report

---

## Additional Resources

### BRSR Resources
- SEBI BRSR Guidelines: https://www.sebi.gov.in/
- BRSR Core Framework: Official SEBI circular
- Sample BRSR Reports: Check listed companies' annual reports

### GRI Resources
- GRI Standards Download: https://www.globalreporting.org/standards/
- GRI Implementation Guide: https://www.globalreporting.org/how-to-use-the-gri-standards/
- Sample GRI Reports: https://database.globalreporting.org/

### Tools
- Microsoft Word: For template creation
- LibreOffice Writer: Free alternative
- python-docx: For programmatic template manipulation
- docxtpl: For template rendering with placeholders

---

## Notes

1. **Version Control**: Keep templates under version control
2. **Annual Updates**: Review and update templates annually
3. **Compliance**: Ensure templates comply with latest standards
4. **Backup**: Maintain backup copies of templates
5. **Testing**: Test templates with sample data before production use

---

## Support

For questions or issues:
- Review official BRSR/GRI documentation
- Check template structure documentation
- Consult sustainability reporting experts
