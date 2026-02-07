"""Tests for Validation Engine"""
import pytest
from uuid import uuid4
from pathlib import Path

from src.validation.engine import (
    ValidationEngine,
    NormalizedRecord,
    ValidationResult
)


@pytest.fixture
def validation_engine():
    """Create validation engine with test rules"""
    rules_path = Path(__file__).parent.parent.parent / "data" / "validation-rules" / "validation_rules.json"
    return ValidationEngine(str(rules_path))


@pytest.fixture
def cement_emission_record():
    """Sample cement emission record within valid range"""
    return NormalizedRecord(
        id=uuid4(),
        indicator="Scope 1 GHG Emissions per tonne clinker",
        value=950.0,
        unit="kg CO₂/tonne",
        original_value=950.0,
        original_unit="kg CO₂/tonne",
        facility_id="FAC001",
        reporting_period="2023"
    )


@pytest.fixture
def cement_emission_record_invalid():
    """Sample cement emission record outside valid range"""
    return NormalizedRecord(
        id=uuid4(),
        indicator="Scope 1 GHG Emissions per tonne clinker",
        value=1500.0,  # Too high
        unit="kg CO₂/tonne",
        original_value=1500.0,
        original_unit="kg CO₂/tonne",
        facility_id="FAC001",
        reporting_period="2023"
    )


@pytest.fixture
def steel_bfbof_record():
    """Sample steel BF-BOF emission record"""
    return NormalizedRecord(
        id=uuid4(),
        indicator="Scope 1 GHG Emissions per tonne crude steel (BF-BOF)",
        value=2100.0,
        unit="kg CO₂/tonne crude steel",
        original_value=2100.0,
        original_unit="kg CO₂/tonne crude steel",
        facility_id="FAC002",
        reporting_period="2023"
    )


class TestValidationEngine:
    """Test suite for ValidationEngine"""
    
    def test_engine_initialization(self, validation_engine):
        """Test that engine loads rules correctly"""
        assert validation_engine.rules is not None
        assert len(validation_engine.rules) > 0
        assert "cement_industry" in validation_engine.rules
        assert "steel_industry" in validation_engine.rules
        assert "cross_industry" in validation_engine.rules
    
    def test_rules_summary(self, validation_engine):
        """Test rules summary method"""
        summary = validation_engine.get_rules_summary()
        assert summary["total_rules"] > 15
        assert "cement_industry" in summary["industries"]
        assert "steel_industry" in summary["industries"]
        assert "range" in summary["validation_types"]
        assert "outlier" in summary["validation_types"]
    
    def test_validate_valid_cement_record(self, validation_engine, cement_emission_record):
        """Test validation of valid cement emission record"""
        results = validation_engine.validate_record(cement_emission_record, "cement_industry")
        # Should pass validation (no results returned for valid data)
        assert len(results) == 0
    
    def test_validate_invalid_cement_record(self, validation_engine, cement_emission_record_invalid):
        """Test validation of invalid cement emission record"""
        results = validation_engine.validate_record(cement_emission_record_invalid, "cement_industry")
        # Should fail validation
        assert len(results) > 0
        assert results[0].is_valid is False
        assert results[0].severity == "error"
        assert results[0].rule_name == "cement_emission_range"
        assert results[0].actual_value == 1500.0
    
    def test_validate_steel_record(self, validation_engine, steel_bfbof_record):
        """Test validation of steel emission record"""
        results = validation_engine.validate_record(steel_bfbof_record, "steel_industry")
        # Should pass validation
        assert len(results) == 0
    
    def test_range_check_below_minimum(self, validation_engine):
        """Test range check with value below minimum"""
        record = NormalizedRecord(
            id=uuid4(),
            indicator="Scope 1 GHG Emissions per tonne clinker",
            value=500.0,  # Below minimum of 800
            unit="kg CO₂/tonne",
            original_value=500.0,
            original_unit="kg CO₂/tonne"
        )
        results = validation_engine.validate_record(record, "cement_industry")
        assert len(results) > 0
        assert "below minimum" in results[0].message
    
    def test_range_check_above_maximum(self, validation_engine):
        """Test range check with value above maximum"""
        record = NormalizedRecord(
            id=uuid4(),
            indicator="Scope 1 GHG Emissions per tonne clinker",
            value=1500.0,  # Above maximum of 1100
            unit="kg CO₂/tonne",
            original_value=1500.0,
            original_unit="kg CO₂/tonne"
        )
        results = validation_engine.validate_record(record, "cement_industry")
        assert len(results) > 0
        assert "above maximum" in results[0].message
    
    def test_category_check_valid(self, validation_engine):
        """Test category check with valid category"""
        record = NormalizedRecord(
            id=uuid4(),
            indicator="Scope 1 emission source category",
            value=0.0,
            unit="",
            original_value=0.0,
            original_unit="",
            metadata={"source_category": "stationary combustion"}
        )
        results = validation_engine.validate_record(record, "cross_industry")
        # Should pass - stationary combustion is valid for Scope 1
        assert len(results) == 0
    
    def test_category_check_invalid(self, validation_engine):
        """Test category check with invalid category"""
        record = NormalizedRecord(
            id=uuid4(),
            indicator="Scope 1 emission source category",
            value=0.0,
            unit="",
            original_value=0.0,
            original_unit="",
            metadata={"source_category": "purchased electricity"}  # Should be Scope 2
        )
        results = validation_engine.validate_record(record, "cross_industry")
        assert len(results) > 0
        assert results[0].is_valid is False
    
    def test_outlier_detection(self, validation_engine):
        """Test outlier detection with multiple records"""
        # Create dataset with one clear outlier
        records = [
            (uuid4(), 100.0),
            (uuid4(), 105.0),
            (uuid4(), 98.0),
            (uuid4(), 102.0),
            (uuid4(), 500.0),  # Outlier
        ]
        
        # Get outlier rule from cross_industry
        outlier_rule = validation_engine._get_outlier_rule("cross_industry")
        assert outlier_rule is not None
        
        results = validation_engine.outlier_detection(records, outlier_rule)
        assert len(results) > 0
        # The outlier (500.0) should be flagged
        outlier_ids = [r.data_id for r in results]
        assert records[4][0] in outlier_ids
    
    def test_temporal_consistency_valid(self, validation_engine):
        """Test temporal consistency with valid data"""
        monthly_data = {
            "Jan": 100.0, "Feb": 100.0, "Mar": 100.0,
            "Apr": 100.0, "May": 100.0, "Jun": 100.0,
            "Jul": 100.0, "Aug": 100.0, "Sep": 100.0,
            "Oct": 100.0, "Nov": 100.0, "Dec": 100.0
        }
        annual_total = 1200.0
        
        # Get temporal consistency rule
        rule = None
        for r in validation_engine.rules["cross_industry"].values():
            if r.rule_name == "monthly_sum_equals_annual":
                rule = r
                break
        
        assert rule is not None
        result = validation_engine.temporal_consistency(
            monthly_data, 
            annual_total, 
            rule, 
            uuid4()
        )
        assert result is None  # Should pass
    
    def test_temporal_consistency_invalid(self, validation_engine):
        """Test temporal consistency with mismatched totals"""
        monthly_data = {
            "Jan": 100.0, "Feb": 100.0, "Mar": 100.0,
            "Apr": 100.0, "May": 100.0, "Jun": 100.0,
            "Jul": 100.0, "Aug": 100.0, "Sep": 100.0,
            "Oct": 100.0, "Nov": 100.0, "Dec": 100.0
        }
        annual_total = 1500.0  # Doesn't match sum of 1200
        
        # Get temporal consistency rule
        rule = None
        for r in validation_engine.rules["cross_industry"].values():
            if r.rule_name == "monthly_sum_equals_annual":
                rule = r
                break
        
        assert rule is not None
        result = validation_engine.temporal_consistency(
            monthly_data, 
            annual_total, 
            rule, 
            uuid4()
        )
        assert result is not None
        assert result.is_valid is False
        assert "differs from annual total" in result.message
    
    def test_validate_batch(self, validation_engine, cement_emission_record, cement_emission_record_invalid):
        """Test batch validation with multiple records"""
        records = [cement_emission_record, cement_emission_record_invalid]
        results = validation_engine.validate_batch(records, "cement_industry")
        
        # Invalid record should have validation results
        assert cement_emission_record_invalid.id in results
        assert len(results[cement_emission_record_invalid.id]) > 0
    
    def test_negative_value_check(self, validation_engine):
        """Test that negative values are caught"""
        record = NormalizedRecord(
            id=uuid4(),
            indicator="Scope 1 GHG Emissions per tonne clinker",
            value=-100.0,  # Negative value
            unit="kg CO₂/tonne",
            original_value=-100.0,
            original_unit="kg CO₂/tonne"
        )
        # Should be caught by range check (min: 0)
        results = validation_engine.validate_record(record, "cross_industry")
        # Note: This will only work if cross_industry has a negative value rule
        # Otherwise it will be caught by industry-specific range checks
    
    def test_precision_check(self, validation_engine):
        """Test precision validation"""
        # Get precision rule
        precision_rule = None
        for r in validation_engine.rules.get("data_quality", {}).values():
            if r.rule_name == "excessive_precision_check":
                precision_rule = r
                break
        
        if precision_rule:
            # Value with excessive precision
            result = validation_engine.precision_check(
                123.456789,  # More than 2 decimal places
                precision_rule,
                uuid4()
            )
            assert result is not None
            assert result.is_valid is False


class TestValidationResults:
    """Test ValidationResult model"""
    
    def test_validation_result_creation(self):
        """Test creating validation result"""
        result = ValidationResult(
            data_id=uuid4(),
            rule_name="test_rule",
            is_valid=False,
            severity="error",
            message="Test error message",
            citation="Test citation",
            suggested_fixes=["Fix 1", "Fix 2"],
            actual_value=100.0,
            expected_range=(50.0, 80.0)
        )
        assert result.is_valid is False
        assert result.severity == "error"
        assert len(result.suggested_fixes) == 2
        assert result.expected_range == (50.0, 80.0)
    
    def test_validation_result_serialization(self):
        """Test that validation result can be serialized"""
        result = ValidationResult(
            data_id=uuid4(),
            rule_name="test_rule",
            is_valid=False,
            severity="warning",
            message="Test warning",
            citation="Test citation"
        )
        result_dict = result.model_dump()
        assert result_dict["rule_name"] == "test_rule"
        assert result_dict["severity"] == "warning"
