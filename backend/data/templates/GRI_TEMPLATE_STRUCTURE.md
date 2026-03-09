# GRI Template Structure

## Overview
Global Reporting Initiative (GRI) Standards template for sustainability reporting.

## Official Source
GRI Standards: https://www.globalreporting.org/standards/

## File Location
`data/templates/gri_template.docx`

## Template Structure

### COVER PAGE

**Placeholders:**
- `{{REPORT_TITLE}}` - Sustainability Report [Year]
- `{{COMPANY_NAME}}` - Organization name
- `{{COMPANY_LOGO}}` - Company logo placeholder
- `{{REPORTING_PERIOD}}` - Reporting period (e.g., January 1 - December 31, 2023)
- `{{PUBLICATION_DATE}}` - Date of publication
- `{{CONTACT_INFO}}` - Contact information for report queries

### TABLE OF CONTENTS

Auto-generated based on sections included

### GRI 2: GENERAL DISCLOSURES (2021)

#### 2-1: Organizational Details

**Placeholders:**
- `{{ORG_NAME}}` - Legal name of organization
- `{{ORG_NATURE}}` - Nature of ownership and legal form
- `{{ORG_LOCATION}}` - Location of headquarters
- `{{ORG_COUNTRIES}}` - Countries of operation

#### 2-2: Entities in Sustainability Reporting

**Placeholders:**
- `{{ENTITIES_LIST}}` - List of entities included in reporting
- `{{CONSOLIDATION_APPROACH}}` - Consolidation approach used

#### 2-3: Reporting Period and Frequency

**Placeholders:**
- `{{REPORTING_PERIOD_START}}` - Start date
- `{{REPORTING_PERIOD_END}}` - End date
- `{{REPORTING_FREQUENCY}}` - Annual/Biennial

#### 2-4: Restatements of Information

**Placeholders:**
- `{{RESTATEMENTS}}` - Any restatements from previous reports

#### 2-5: External Assurance

**Placeholders:**
- `{{ASSURANCE_PROVIDER}}` - External assurance provider
- `{{ASSURANCE_SCOPE}}` - Scope of assurance
- `{{ASSURANCE_STATEMENT}}` - Link to assurance statement

#### 2-6: Activities, Value Chain and Business Relationships

**Placeholders:**
- `{{SECTOR}}` - Sector(s) in which active
- `{{VALUE_CHAIN}}` - Description of value chain
- `{{BUSINESS_RELATIONSHIPS}}` - Significant business relationships

#### 2-7: Employees

**Placeholders:**
- `{{TOTAL_EMPLOYEES}}` - Total number of employees
- `{{EMPLOYEES_BY_GENDER}}` - Breakdown by gender
- `{{EMPLOYEES_BY_REGION}}` - Breakdown by region
- `{{EMPLOYEES_BY_CONTRACT}}` - Permanent vs temporary

#### 2-8: Workers Who Are Not Employees

**Placeholders:**
- `{{CONTRACTORS}}` - Number of contractors
- `{{WORKERS_DESCRIPTION}}` - Description of work performed

#### 2-9: Governance Structure

**Placeholders:**
- `{{GOVERNANCE_STRUCTURE}}` - Governance structure description
- `{{BOARD_COMPOSITION}}` - Board composition
- `{{COMMITTEES}}` - Committees responsible for sustainability

#### 2-10 to 2-21: Additional Governance Disclosures

**Placeholders for:**
- Nomination and selection
- Chair of highest governance body
- Role in sustainability oversight
- Delegation of responsibility
- Conflicts of interest
- Communication of critical concerns
- Collective knowledge
- Performance evaluation
- Remuneration policies
- Process for determining remuneration
- Annual total compensation ratio
- Statement on sustainable development strategy

#### 2-22: Strategy on Sustainable Development

**Placeholders:**
- `{{SUSTAINABILITY_STRATEGY}}` - Overall sustainability strategy
- `{{COMMITMENTS}}` - Key commitments and targets

#### 2-23 to 2-30: Additional Disclosures

**Placeholders for:**
- Policy commitments
- Embedding policy commitments
- Processes to remediate negative impacts
- Mechanisms for seeking advice
- Compliance with laws and regulations
- Membership associations
- Approach to stakeholder engagement
- Collective bargaining agreements

### GRI 302: ENERGY (2016)

#### 302-1: Energy Consumption Within the Organization

**Placeholders:**
- `{{ENERGY_FUEL_CONSUMPTION_GJ}}` - Total fuel consumption from non-renewable sources (GJ)
- `{{ENERGY_FUEL_RENEWABLE_GJ}}` - Total fuel consumption from renewable sources (GJ)
- `{{ENERGY_ELECTRICITY_PURCHASED_GJ}}` - Electricity purchased (GJ)
- `{{ENERGY_ELECTRICITY_RENEWABLE_GJ}}` - Renewable electricity purchased (GJ)
- `{{ENERGY_HEATING_PURCHASED_GJ}}` - Heating purchased (GJ)
- `{{ENERGY_COOLING_PURCHASED_GJ}}` - Cooling purchased (GJ)
- `{{ENERGY_STEAM_PURCHASED_GJ}}` - Steam purchased (GJ)
- `{{ENERGY_TOTAL_GJ}}` - Total energy consumption (GJ)
- `{{ENERGY_TOTAL_MWH}}` - Total energy consumption (MWh)

#### 302-2: Energy Consumption Outside the Organization

**Placeholders:**
- `{{ENERGY_UPSTREAM_GJ}}` - Energy consumption in upstream activities (GJ)
- `{{ENERGY_DOWNSTREAM_GJ}}` - Energy consumption in downstream activities (GJ)

#### 302-3: Energy Intensity

**Placeholders:**
- `{{ENERGY_INTENSITY_RATIO}}` - Energy intensity ratio
- `{{ENERGY_INTENSITY_DENOMINATOR}}` - Organization-specific metric (denominator)
- `{{ENERGY_INTENSITY_TYPES}}` - Types of energy included

#### 302-4: Reduction of Energy Consumption

**Placeholders:**
- `{{ENERGY_REDUCTION_GJ}}` - Energy reductions achieved (GJ)
- `{{ENERGY_REDUCTION_INITIATIVES}}` - Description of initiatives
- `{{ENERGY_BASELINE_YEAR}}` - Baseline year for calculations

#### 302-5: Reductions in Energy Requirements

**Placeholders:**
- `{{ENERGY_PRODUCTS_REDUCTION}}` - Reductions in energy requirements of products/services
- `{{ENERGY_PRODUCTS_BASELINE}}` - Baseline year for calculations

### GRI 305: EMISSIONS (2016)

#### 305-1: Direct (Scope 1) GHG Emissions

**Placeholders:**
- `{{GHG_SCOPE1_TONNES}}` - Gross direct (Scope 1) GHG emissions (tonnes CO₂e)
- `{{GHG_SCOPE1_GASES}}` - Gases included in calculation
- `{{GHG_SCOPE1_BIOGENIC}}` - Biogenic CO₂ emissions (tonnes CO₂)
- `{{GHG_SCOPE1_BASE_YEAR}}` - Base year for calculation
- `{{GHG_SCOPE1_METHODOLOGY}}` - Methodology used

#### 305-2: Energy Indirect (Scope 2) GHG Emissions

**Placeholders:**
- `{{GHG_SCOPE2_LOCATION_TONNES}}` - Scope 2 emissions (location-based) (tonnes CO₂e)
- `{{GHG_SCOPE2_MARKET_TONNES}}` - Scope 2 emissions (market-based) (tonnes CO₂e)
- `{{GHG_SCOPE2_GASES}}` - Gases included
- `{{GHG_SCOPE2_BASE_YEAR}}` - Base year
- `{{GHG_SCOPE2_METHODOLOGY}}` - Methodology used

#### 305-3: Other Indirect (Scope 3) GHG Emissions

**Placeholders:**
- `{{GHG_SCOPE3_TONNES}}` - Gross other indirect (Scope 3) GHG emissions (tonnes CO₂e)
- `{{GHG_SCOPE3_CATEGORIES}}` - Scope 3 categories included
- `{{GHG_SCOPE3_BIOGENIC}}` - Biogenic CO₂ emissions
- `{{GHG_SCOPE3_METHODOLOGY}}` - Methodology used

#### 305-4: GHG Emissions Intensity

**Placeholders:**
- `{{GHG_INTENSITY_RATIO}}` - GHG emissions intensity ratio
- `{{GHG_INTENSITY_DENOMINATOR}}` - Organization-specific metric
- `{{GHG_INTENSITY_SCOPES}}` - Scopes included in calculation

#### 305-5: Reduction of GHG Emissions

**Placeholders:**
- `{{GHG_REDUCTION_TONNES}}` - GHG emissions reduced (tonnes CO₂e)
- `{{GHG_REDUCTION_INITIATIVES}}` - Description of initiatives
- `{{GHG_REDUCTION_BASELINE}}` - Baseline year
- `{{GHG_REDUCTION_SCOPES}}` - Scopes included

#### 305-6: Emissions of Ozone-Depleting Substances

**Placeholders:**
- `{{ODS_EMISSIONS}}` - Production, imports, exports of ODS (tonnes CFC-11 equivalent)

#### 305-7: NOx, SOx, and Other Significant Air Emissions

**Placeholders:**
- `{{NOX_EMISSIONS_TONNES}}` - NOx emissions (tonnes)
- `{{SOX_EMISSIONS_TONNES}}` - SOx emissions (tonnes)
- `{{PM_EMISSIONS_TONNES}}` - Particulate matter (PM) emissions (tonnes)
- `{{VOC_EMISSIONS_TONNES}}` - Volatile organic compounds (VOC) (tonnes)
- `{{HAP_EMISSIONS_TONNES}}` - Hazardous air pollutants (HAP) (tonnes)
- `{{OTHER_AIR_EMISSIONS}}` - Other significant air emissions

### GRI 303: WATER AND EFFLUENTS (2018)

#### 303-1: Interactions with Water as a Shared Resource

**Placeholders:**
- `{{WATER_WITHDRAWAL_DESCRIPTION}}` - Description of water withdrawal
- `{{WATER_DISCHARGE_DESCRIPTION}}` - Description of water discharge
- `{{WATER_CONSUMPTION_DESCRIPTION}}` - Description of water consumption

#### 303-2: Management of Water Discharge-Related Impacts

**Placeholders:**
- `{{WATER_DISCHARGE_STANDARDS}}` - Standards for water discharge
- `{{WATER_DISCHARGE_APPROACH}}` - Approach to managing impacts

#### 303-3: Water Withdrawal

**Placeholders:**
- `{{WATER_WITHDRAWAL_TOTAL_ML}}` - Total water withdrawal (megaliters)
- `{{WATER_WITHDRAWAL_SURFACE_ML}}` - Surface water withdrawal (ML)
- `{{WATER_WITHDRAWAL_GROUNDWATER_ML}}` - Groundwater withdrawal (ML)
- `{{WATER_WITHDRAWAL_SEAWATER_ML}}` - Seawater withdrawal (ML)
- `{{WATER_WITHDRAWAL_PRODUCED_ML}}` - Produced water withdrawal (ML)
- `{{WATER_WITHDRAWAL_THIRD_PARTY_ML}}` - Third-party water withdrawal (ML)
- `{{WATER_STRESS_AREAS}}` - Withdrawal from water-stressed areas

#### 303-4: Water Discharge

**Placeholders:**
- `{{WATER_DISCHARGE_TOTAL_ML}}` - Total water discharge (megaliters)
- `{{WATER_DISCHARGE_SURFACE_ML}}` - To surface water (ML)
- `{{WATER_DISCHARGE_GROUNDWATER_ML}}` - To groundwater (ML)
- `{{WATER_DISCHARGE_SEAWATER_ML}}` - To seawater (ML)
- `{{WATER_DISCHARGE_THIRD_PARTY_ML}}` - To third parties (ML)
- `{{WATER_DISCHARGE_QUALITY}}` - Water quality parameters

#### 303-5: Water Consumption

**Placeholders:**
- `{{WATER_CONSUMPTION_TOTAL_ML}}` - Total water consumption (megaliters)
- `{{WATER_CONSUMPTION_STRESS_AREAS_ML}}` - Consumption in water-stressed areas (ML)
- `{{WATER_CONSUMPTION_CHANGE}}` - Change in water storage (ML)

### GRI 306: WASTE (2020)

#### 306-1: Waste Generation and Significant Waste-Related Impacts

**Placeholders:**
- `{{WASTE_GENERATION_INPUTS}}` - Inputs, activities, outputs causing waste
- `{{WASTE_IMPACTS_DESCRIPTION}}` - Description of significant impacts

#### 306-2: Management of Significant Waste-Related Impacts

**Placeholders:**
- `{{WASTE_MANAGEMENT_ACTIONS}}` - Actions to prevent waste generation
- `{{WASTE_MANAGEMENT_CIRCULAR}}` - Circular economy practices

#### 306-3: Waste Generated

**Placeholders:**
- `{{WASTE_TOTAL_TONNES}}` - Total waste generated (tonnes)
- `{{WASTE_HAZARDOUS_TONNES}}` - Hazardous waste (tonnes)
- `{{WASTE_NON_HAZARDOUS_TONNES}}` - Non-hazardous waste (tonnes)
- `{{WASTE_COMPOSITION}}` - Composition of waste

#### 306-4: Waste Diverted from Disposal

**Placeholders:**
- `{{WASTE_DIVERTED_TOTAL_TONNES}}` - Total waste diverted (tonnes)
- `{{WASTE_DIVERTED_HAZARDOUS_TONNES}}` - Hazardous waste diverted (tonnes)
- `{{WASTE_DIVERTED_NON_HAZARDOUS_TONNES}}` - Non-hazardous waste diverted (tonnes)
- `{{WASTE_REUSE_TONNES}}` - Waste prepared for reuse (tonnes)
- `{{WASTE_RECYCLING_TONNES}}` - Waste recycled (tonnes)
- `{{WASTE_OTHER_RECOVERY_TONNES}}` - Other recovery operations (tonnes)

#### 306-5: Waste Directed to Disposal

**Placeholders:**
- `{{WASTE_DISPOSAL_TOTAL_TONNES}}` - Total waste to disposal (tonnes)
- `{{WASTE_DISPOSAL_HAZARDOUS_TONNES}}` - Hazardous waste to disposal (tonnes)
- `{{WASTE_DISPOSAL_NON_HAZARDOUS_TONNES}}` - Non-hazardous waste to disposal (tonnes)
- `{{WASTE_INCINERATION_TONNES}}` - Incineration (tonnes)
- `{{WASTE_LANDFILL_TONNES}}` - Landfill (tonnes)
- `{{WASTE_OTHER_DISPOSAL_TONNES}}` - Other disposal operations (tonnes)

### ADDITIONAL TOPIC-SPECIFIC STANDARDS

Organizations should include additional GRI topic standards based on materiality assessment:

- GRI 201: Economic Performance
- GRI 202: Market Presence
- GRI 203: Indirect Economic Impacts
- GRI 204: Procurement Practices
- GRI 205: Anti-corruption
- GRI 206: Anti-competitive Behavior
- GRI 301: Materials
- GRI 304: Biodiversity
- GRI 307: Environmental Compliance
- GRI 308: Supplier Environmental Assessment
- GRI 401: Employment
- GRI 402: Labor/Management Relations
- GRI 403: Occupational Health and Safety
- GRI 404: Training and Education
- GRI 405: Diversity and Equal Opportunity
- GRI 406: Non-discrimination
- GRI 407: Freedom of Association
- GRI 408: Child Labor
- GRI 409: Forced or Compulsory Labor
- GRI 410: Security Practices
- GRI 411: Rights of Indigenous Peoples
- GRI 413: Local Communities
- GRI 414: Supplier Social Assessment
- GRI 415: Public Policy
- GRI 416: Customer Health and Safety
- GRI 417: Marketing and Labeling
- GRI 418: Customer Privacy

## Data Mapping

### From Normalized Data to GRI

```python
# Energy mapping (GRI 302)
normalized_data["Total Electricity Consumption"] * 3.6 -> {{ENERGY_TOTAL_GJ}}
normalized_data["Total Electricity Consumption"] -> {{ENERGY_TOTAL_MWH}}

# Emissions mapping (GRI 305)
normalized_data["Scope 1 Emissions"] -> {{GHG_SCOPE1_TONNES}}
normalized_data["Scope 2 Emissions"] -> {{GHG_SCOPE2_LOCATION_TONNES}}
normalized_data["Scope 3 Emissions"] -> {{GHG_SCOPE3_TONNES}}

# Water mapping (GRI 303)
normalized_data["Total Water Consumption"] / 1000 -> {{WATER_CONSUMPTION_TOTAL_ML}}
normalized_data["Water Withdrawal"] / 1000 -> {{WATER_WITHDRAWAL_TOTAL_ML}}

# Waste mapping (GRI 306)
normalized_data["Total Waste Generated"] -> {{WASTE_TOTAL_TONNES}}
normalized_data["Hazardous Waste"] -> {{WASTE_HAZARDOUS_TONNES}}
normalized_data["Waste Recycled"] -> {{WASTE_RECYCLING_TONNES}}
```

## Formatting Guidelines

1. **Font**: Arial 10pt for body text, Arial 14pt Bold for section headings
2. **Margins**: 1 inch on all sides
3. **Line Spacing**: 1.5
4. **Tables**: Use GRI-compliant table formats
5. **Headers/Footers**: Include report title and page numbers
6. **Colors**: Use organization's brand colors
7. **Charts/Graphs**: Include visual representations of key data

## GRI Content Index

Include a GRI Content Index table mapping each disclosure to page numbers:

| GRI Standard | Disclosure | Page Number | Omission |
|--------------|------------|-------------|----------|
| GRI 2-1 | Organizational details | X | - |
| GRI 302-1 | Energy consumption | X | - |
| ... | ... | ... | ... |

## Notes

- Report must be "in accordance" with GRI Standards
- Include materiality assessment results
- Provide comparative data for at least 2 years
- Consider external assurance for credibility
- Publish report publicly (website, sustainability platforms)
