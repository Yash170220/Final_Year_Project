# BRSR Template Structure

## Overview
Business Responsibility and Sustainability Reporting (BRSR) template based on SEBI guidelines for listed entities in India.

## Official Source
Download official template from SEBI:
https://www.sebi.gov.in/legal/circulars/jul-2023/business-responsibility-and-sustainability-reporting-by-listed-entities_73592.html

## File Location
`data/templates/brsr_template.docx`

## Template Structure

### SECTION A: GENERAL DISCLOSURES

#### I. Details of the Listed Entity

**Placeholders:**
- `{{COMPANY_NAME}}` - Corporate Identity Number
- `{{CIN}}` - Corporate Identity Number
- `{{REGISTERED_OFFICE}}` - Complete registered office address
- `{{CORPORATE_OFFICE}}` - Corporate office address (if different)
- `{{EMAIL}}` - Contact email
- `{{TELEPHONE}}` - Contact telephone
- `{{WEBSITE}}` - Company website
- `{{FINANCIAL_YEAR}}` - Reporting financial year (e.g., 2023-24)
- `{{STOCK_EXCHANGES}}` - List of stock exchanges where listed
- `{{PAID_UP_CAPITAL}}` - Paid-up capital in INR
- `{{CONTACT_PERSON}}` - Name of contact person for BRSR
- `{{CONTACT_EMAIL}}` - Email of contact person
- `{{CONTACT_PHONE}}` - Phone of contact person

#### II. Products/Services

**Placeholders:**
- `{{BUSINESS_ACTIVITIES}}` - Description of main business activities
- `{{PRODUCTS_SERVICES}}` - List of products/services with NIC codes
- `{{REVENUE_CONTRIBUTION}}` - Revenue contribution by product/service

#### III. Operations

**Placeholders:**
- `{{NUM_LOCATIONS}}` - Number of locations where operations/offices
- `{{NUM_PLANTS}}` - Number of manufacturing plants
- `{{NATIONAL_LOCATIONS}}` - List of national locations
- `{{INTERNATIONAL_LOCATIONS}}` - List of international locations

#### IV. Employees

**Placeholders:**
- `{{TOTAL_EMPLOYEES}}` - Total number of employees
- `{{PERMANENT_EMPLOYEES}}` - Number of permanent employees
- `{{MALE_EMPLOYEES}}` - Number of male employees
- `{{FEMALE_EMPLOYEES}}` - Number of female employees
- `{{WORKERS}}` - Number of workers
- `{{DIFFERENTLY_ABLED}}` - Number of differently abled employees

#### V. Holding, Subsidiary and Associate Companies

**Placeholders:**
- `{{SUBSIDIARY_COMPANIES}}` - List of subsidiary companies
- `{{ASSOCIATE_COMPANIES}}` - List of associate companies

#### VI. CSR Details

**Placeholders:**
- `{{CSR_COMMITTEE}}` - CSR committee details
- `{{CSR_EXPENDITURE}}` - CSR expenditure amount
- `{{CSR_PROJECTS}}` - List of CSR projects

### SECTION B: MANAGEMENT AND PROCESS DISCLOSURES

#### Policy and Management Processes

**Placeholders:**
- `{{POLICY_ETHICS}}` - Ethics and business conduct policy
- `{{POLICY_SUSTAINABILITY}}` - Sustainability policy
- `{{POLICY_HUMAN_RIGHTS}}` - Human rights policy
- `{{BOARD_OVERSIGHT}}` - Board oversight mechanisms
- `{{STAKEHOLDER_ENGAGEMENT}}` - Stakeholder engagement process

### SECTION C: PRINCIPLE-WISE PERFORMANCE DISCLOSURE

#### Principle 1: Ethics, Transparency and Accountability

**Placeholders:**
- `{{P1_POLICY}}` - Policy details
- `{{P1_GRIEVANCES}}` - Grievance mechanism
- `{{P1_COMPLAINTS}}` - Number of complaints received/resolved

#### Principle 2: Product Lifecycle Sustainability

**Placeholders:**
- `{{P2_SUSTAINABLE_PRODUCTS}}` - Percentage of sustainable products
- `{{P2_RECYCLED_INPUT}}` - Percentage of recycled input materials
- `{{P2_WASTE_RECLAIMED}}` - Percentage of waste reclaimed

#### Principle 3: Employee Well-being

**Placeholders:**
- `{{P3_TRAINING_HOURS}}` - Average training hours per employee
- `{{P3_SAFETY_INCIDENTS}}` - Number of safety incidents
- `{{P3_ATTRITION_RATE}}` - Employee attrition rate

#### Principle 4: Stakeholder Engagement

**Placeholders:**
- `{{P4_STAKEHOLDER_GROUPS}}` - List of stakeholder groups
- `{{P4_ENGAGEMENT_FREQUENCY}}` - Engagement frequency

#### Principle 5: Human Rights

**Placeholders:**
- `{{P5_HUMAN_RIGHTS_TRAINING}}` - Human rights training coverage
- `{{P5_COMPLAINTS}}` - Human rights complaints

#### Principle 6: Environment

**Essential Environmental Metrics:**

**Energy Consumption:**
- `{{ENERGY_TOTAL_MWH}}` - Total energy consumption in MWh
- `{{ENERGY_RENEWABLE_MWH}}` - Renewable energy in MWh
- `{{ENERGY_INTENSITY}}` - Energy intensity (MWh/unit of output)
- `{{ENERGY_REDUCTION_TARGET}}` - Energy reduction target %

**Water Consumption:**
- `{{WATER_TOTAL_M3}}` - Total water consumption in m³
- `{{WATER_RECYCLED_M3}}` - Water recycled/reused in m³
- `{{WATER_INTENSITY}}` - Water intensity (m³/unit of output)
- `{{WATER_STRESS_AREAS}}` - Operations in water-stressed areas

**Emissions:**
- `{{GHG_SCOPE1_TONNES}}` - Scope 1 GHG emissions in tonnes CO₂e
- `{{GHG_SCOPE2_TONNES}}` - Scope 2 GHG emissions in tonnes CO₂e
- `{{GHG_SCOPE3_TONNES}}` - Scope 3 GHG emissions in tonnes CO₂e (if available)
- `{{GHG_TOTAL_TONNES}}` - Total GHG emissions in tonnes CO₂e
- `{{GHG_INTENSITY}}` - GHG intensity (tonnes CO₂e/unit of output)
- `{{GHG_REDUCTION_TARGET}}` - GHG reduction target %

**Waste Management:**
- `{{WASTE_TOTAL_TONNES}}` - Total waste generated in tonnes
- `{{WASTE_HAZARDOUS_TONNES}}` - Hazardous waste in tonnes
- `{{WASTE_RECYCLED_TONNES}}` - Waste recycled in tonnes
- `{{WASTE_LANDFILL_TONNES}}` - Waste to landfill in tonnes
- `{{WASTE_INTENSITY}}` - Waste intensity (tonnes/unit of output)

**Air Quality:**
- `{{NOX_EMISSIONS}}` - NOx emissions
- `{{SOX_EMISSIONS}}` - SOx emissions
- `{{PM_EMISSIONS}}` - Particulate matter emissions

#### Principle 7: Policy Advocacy

**Placeholders:**
- `{{P7_TRADE_ASSOCIATIONS}}` - Trade associations membership
- `{{P7_POLICY_POSITIONS}}` - Policy advocacy positions

#### Principle 8: Inclusive Growth

**Placeholders:**
- `{{P8_LOCAL_EMPLOYMENT}}` - Percentage of local employment
- `{{P8_LOCAL_PROCUREMENT}}` - Percentage of local procurement
- `{{P8_COMMUNITY_PROGRAMS}}` - Community development programs

#### Principle 9: Customer Value

**Placeholders:**
- `{{P9_CUSTOMER_COMPLAINTS}}` - Customer complaints received/resolved
- `{{P9_PRODUCT_RECALLS}}` - Product recalls
- `{{P9_CUSTOMER_SATISFACTION}}` - Customer satisfaction score

### SECTION D: ADDITIONAL DISCLOSURES

**Placeholders:**
- `{{ADDITIONAL_INITIATIVES}}` - Additional sustainability initiatives
- `{{AWARDS_RECOGNITION}}` - Awards and recognition received
- `{{FUTURE_COMMITMENTS}}` - Future sustainability commitments

## Data Mapping

### From Normalized Data to BRSR

```python
# Energy mapping
normalized_data["Total Electricity Consumption"] -> {{ENERGY_TOTAL_MWH}}
normalized_data["Renewable Energy"] -> {{ENERGY_RENEWABLE_MWH}}

# Emissions mapping
normalized_data["Scope 1 Emissions"] -> {{GHG_SCOPE1_TONNES}}
normalized_data["Scope 2 Emissions"] -> {{GHG_SCOPE2_TONNES}}

# Water mapping
normalized_data["Total Water Consumption"] -> {{WATER_TOTAL_M3}}
normalized_data["Water Recycled"] -> {{WATER_RECYCLED_M3}}

# Waste mapping
normalized_data["Total Waste Generated"] -> {{WASTE_TOTAL_TONNES}}
normalized_data["Hazardous Waste"] -> {{WASTE_HAZARDOUS_TONNES}}
```

## Formatting Guidelines

1. **Font**: Arial 11pt for body text, Arial 12pt Bold for headings
2. **Margins**: 1 inch on all sides
3. **Line Spacing**: 1.15
4. **Tables**: Use bordered tables for data presentation
5. **Headers/Footers**: Include company name and page numbers
6. **Logo**: Company logo on first page (top right)

## Validation Rules

- All monetary values in INR Crores
- All percentages with 2 decimal places
- All dates in DD-MM-YYYY format
- All quantities with appropriate units
- Scope 1+2 emissions mandatory, Scope 3 optional

## Notes

- Template must be updated annually per SEBI guidelines
- All data must be audited/verified
- Comparative data for previous 2 years recommended
- Assurance statement from independent auditor required
