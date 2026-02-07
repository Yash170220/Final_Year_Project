"""Validation Engine for ESG Data Quality Control"""
import json
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field


class ValidationRule(BaseModel):
    """Schema for validation rule"""
    rule_name: str
    description: str
    indicator: str
    validation_type: str
    parameters: Dict[str, Any]
    severity: str
    citation: str
    error_message: str
    suggested_fixes: List[str] = Field(default_factory=list)


class NormalizedRecord(BaseModel):
    """Schema for normalized data record"""
    id: UUID
    indicator: str
    value: float
    unit: str
    original_value: float
    original_unit: str
    facility_id: Optional[str] = None
    reporting_period: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ValidationResult(BaseModel):
    """Schema for validation result"""
    data_id: UUID
    rule_name: str
    is_valid: bool
    severity: str  # "error" | "warning"
    message: str
    citation: str
    suggested_fixes: List[str] = Field(default_factory=list)
    actual_value: Optional[float] = None
    expected_range: Optional[Tuple[float, float]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationEngine:
    """Engine for validating ESG data against industry-specific rules"""
    
    def __init__(self, rules_path: str):
        """
        Initialize validation engine with rules from JSON file
        
        Args:
            rules_path: Path to validation_rules.json file
        """
        self.rules_path = Path(rules_path)
        self.rules: Dict[str, Dict[str, ValidationRule]] = {}
        self.rules_index: Dict[str, List[ValidationRule]] = {}
        
        self._load_rules()
        self._index_rules()
    
    def _load_rules(self) -> None:
        """Load validation rules from JSON file"""
        if not self.rules_path.exists():
            raise FileNotFoundError(f"Validation rules file not found: {self.rules_path}")
        
        with open(self.rules_path, 'r', encoding='utf-8') as f:
            raw_rules = json.load(f)
        
        # Parse rules into ValidationRule objects
        for industry, industry_rules in raw_rules.items():
            self.rules[industry] = {}
            for rule_key, rule_data in industry_rules.items():
                self.rules[industry][rule_key] = ValidationRule(**rule_data)
    
    def _index_rules(self) -> None:
        """Index rules by industry and indicator for fast lookup"""
        for industry, industry_rules in self.rules.items():
            for rule_key, rule in industry_rules.items():
                # Index by industry
                index_key = f"{industry}"
                if index_key not in self.rules_index:
                    self.rules_index[index_key] = []
                self.rules_index[index_key].append(rule)
                
                # Index by indicator if present
                if rule.indicator:
                    indicator_key = f"{industry}:{rule.indicator}"
                    if indicator_key not in self.rules_index:
                        self.rules_index[indicator_key] = []
                    self.rules_index[indicator_key].append(rule)
    
    def validate_record(
        self, 
        record: NormalizedRecord, 
        industry: str
    ) -> List[ValidationResult]:
        """
        Validate a single record against applicable rules
        
        Args:
            record: Normalized data record to validate
            industry: Industry category (e.g., "cement_industry", "steel_industry")
        
        Returns:
            List of validation results (only failed validations)
        """
        results: List[ValidationResult] = []
        
        # Get applicable rules for this industry and indicator
        applicable_rules = self._get_applicable_rules(industry, record.indicator)
        
        if not applicable_rules:
            # Check cross-industry rules
            applicable_rules = self._get_applicable_rules("cross_industry", record.indicator)
        
        # Run each applicable rule
        for rule in applicable_rules:
            result = self._execute_validation(record, rule)
            if result:  # Only add failed validations
                results.append(result)
        
        return results
    
    def _get_applicable_rules(self, industry: str, indicator: str) -> List[ValidationRule]:
        """Get rules applicable to given industry and indicator"""
        rules = []
        
        # Try exact match with indicator
        indicator_key = f"{industry}:{indicator}"
        if indicator_key in self.rules_index:
            rules.extend(self.rules_index[indicator_key])
        
        # Get all industry rules (may apply to multiple indicators)
        industry_key = industry
        if industry_key in self.rules_index:
            for rule in self.rules_index[industry_key]:
                # Add rule if indicator matches or rule applies to all indicators
                if rule.indicator == indicator or not rule.indicator:
                    if rule not in rules:
                        rules.append(rule)
        
        return rules
    
    def _execute_validation(
        self, 
        record: NormalizedRecord, 
        rule: ValidationRule
    ) -> Optional[ValidationResult]:
        """Execute appropriate validation based on rule type"""
        validation_type = rule.validation_type
        
        if validation_type == "range":
            return self.range_check(record.value, rule, record.id)
        elif validation_type == "category_check":
            return self.category_check(
                record.metadata.get("source_category", ""), 
                rule, 
                record.id
            )
        elif validation_type == "outlier":
            # Note: Outlier detection needs multiple values, 
            # this is handled in validate_batch method
            return None
        elif validation_type == "pattern_match":
            return self.pattern_match(record.unit, rule, record.id)
        elif validation_type == "null_check":
            return self.null_check(record, rule)
        elif validation_type == "precision_check":
            return self.precision_check(record.value, rule, record.id)
        else:
            # Unknown validation type
            return None
    
    def range_check(
        self, 
        value: float, 
        rule: ValidationRule, 
        data_id: UUID
    ) -> Optional[ValidationResult]:
        """
        Check if value is within acceptable range
        
        Args:
            value: Numeric value to check
            rule: Validation rule with min/max parameters
            data_id: ID of the data record being validated
        
        Returns:
            ValidationResult if check fails, None if passes
        """
        min_val = rule.parameters.get("min")
        max_val = rule.parameters.get("max")
        
        # Handle cases where min or max might be None
        if min_val is not None and value < min_val:
            return ValidationResult(
                data_id=data_id,
                rule_name=rule.rule_name,
                is_valid=False,
                severity=rule.severity,
                message=f"{rule.error_message} Value {value} is below minimum {min_val}.",
                citation=rule.citation,
                suggested_fixes=rule.suggested_fixes,
                actual_value=value,
                expected_range=(min_val, max_val) if max_val else None
            )
        
        if max_val is not None and value > max_val:
            return ValidationResult(
                data_id=data_id,
                rule_name=rule.rule_name,
                is_valid=False,
                severity=rule.severity,
                message=f"{rule.error_message} Value {value} is above maximum {max_val}.",
                citation=rule.citation,
                suggested_fixes=rule.suggested_fixes,
                actual_value=value,
                expected_range=(min_val, max_val) if min_val else None
            )
        
        # Value is within range
        return None
    
    def category_check(
        self, 
        value: str, 
        rule: ValidationRule, 
        data_id: UUID
    ) -> Optional[ValidationResult]:
        """
        Check if value is in allowed categories
        
        Args:
            value: Category value to check
            rule: Validation rule with allowed_sources or allowed categories
            data_id: ID of the data record
        
        Returns:
            ValidationResult if check fails, None if passes
        """
        allowed_categories = (
            rule.parameters.get("allowed_sources", []) or 
            rule.parameters.get("allowed_categories", [])
        )
        
        if value.lower() not in [cat.lower() for cat in allowed_categories]:
            return ValidationResult(
                data_id=data_id,
                rule_name=rule.rule_name,
                is_valid=False,
                severity=rule.severity,
                message=f"{rule.error_message} Found '{value}', expected one of: {', '.join(allowed_categories)}",
                citation=rule.citation,
                suggested_fixes=rule.suggested_fixes
            )
        
        return None
    
    def outlier_detection(
        self, 
        values: List[Tuple[UUID, float]], 
        rule: ValidationRule
    ) -> List[ValidationResult]:
        """
        Detect statistical outliers using z-score method
        
        Args:
            values: List of (data_id, value) tuples
            rule: Validation rule with z_score_threshold parameter
        
        Returns:
            List of ValidationResults for detected outliers
        """
        if len(values) < 3:
            # Need at least 3 values for meaningful statistics
            return []
        
        results: List[ValidationResult] = []
        threshold = rule.parameters.get("z_score_threshold", 3.0)
        
        # Extract just the values for statistics
        numeric_values = [v[1] for v in values]
        
        # Calculate mean and standard deviation
        mean = statistics.mean(numeric_values)
        stdev = statistics.stdev(numeric_values) if len(numeric_values) > 1 else 0
        
        if stdev == 0:
            # All values are the same, no outliers
            return results
        
        # Check each value for outlier status
        for data_id, value in values:
            z_score = abs((value - mean) / stdev)
            
            if z_score > threshold:
                results.append(ValidationResult(
                    data_id=data_id,
                    rule_name=rule.rule_name,
                    is_valid=False,
                    severity=rule.severity,
                    message=f"{rule.error_message} Z-score: {z_score:.2f} (threshold: {threshold})",
                    citation=rule.citation,
                    suggested_fixes=rule.suggested_fixes,
                    actual_value=value,
                    expected_range=(mean - threshold * stdev, mean + threshold * stdev)
                ))
        
        return results
    
    def temporal_consistency(
        self, 
        monthly_data: Dict[str, float], 
        annual_total: float, 
        rule: ValidationRule,
        data_id: UUID
    ) -> Optional[ValidationResult]:
        """
        Check if monthly values sum to annual total
        
        Args:
            monthly_data: Dictionary of month -> value
            annual_total: Expected annual sum
            rule: Validation rule with tolerance parameter
            data_id: ID of the annual data record
        
        Returns:
            ValidationResult if check fails, None if passes
        """
        if not monthly_data:
            return None
        
        monthly_sum = sum(monthly_data.values())
        tolerance = rule.parameters.get("tolerance", 0.02)  # Default 2%
        
        # Calculate percentage difference
        if annual_total == 0:
            diff_pct = abs(monthly_sum) / 1.0  # Avoid division by zero
        else:
            diff_pct = abs(monthly_sum - annual_total) / annual_total
        
        if diff_pct > tolerance:
            return ValidationResult(
                data_id=data_id,
                rule_name=rule.rule_name,
                is_valid=False,
                severity=rule.severity,
                message=(
                    f"Monthly sum ({monthly_sum:.2f}) differs from annual total "
                    f"({annual_total:.2f}) by {diff_pct*100:.1f}% "
                    f"(tolerance: {tolerance*100:.1f}%)"
                ),
                citation=rule.citation,
                suggested_fixes=rule.suggested_fixes,
                actual_value=monthly_sum,
                expected_range=(
                    annual_total * (1 - tolerance),
                    annual_total * (1 + tolerance)
                )
            )
        
        return None
    
    def pattern_match(
        self, 
        value: str, 
        rule: ValidationRule, 
        data_id: UUID
    ) -> Optional[ValidationResult]:
        """
        Check if value matches allowed patterns (e.g., unit formats)
        
        Args:
            value: String value to check
            rule: Validation rule with allowed_patterns parameter
            data_id: ID of the data record
        
        Returns:
            ValidationResult if check fails, None if passes
        """
        allowed_patterns = rule.parameters.get("allowed_patterns", [])
        
        # Simple pattern matching (exact match or substring)
        if not any(pattern in value for pattern in allowed_patterns):
            return ValidationResult(
                data_id=data_id,
                rule_name=rule.rule_name,
                is_valid=False,
                severity=rule.severity,
                message=f"{rule.error_message} Found '{value}', expected pattern from: {', '.join(allowed_patterns)}",
                citation=rule.citation,
                suggested_fixes=rule.suggested_fixes
            )
        
        return None
    
    def null_check(
        self, 
        record: NormalizedRecord, 
        rule: ValidationRule
    ) -> Optional[ValidationResult]:
        """
        Check for required fields that are null or empty
        
        Args:
            record: Data record to check
            rule: Validation rule with required_fields parameter
        
        Returns:
            ValidationResult if check fails, None if passes
        """
        required_fields = rule.parameters.get("required_fields", [])
        missing_fields = []
        
        # Convert record to dict for field checking
        record_dict = record.model_dump()
        record_dict.update(record.metadata)
        
        for field in required_fields:
            value = record_dict.get(field)
            if value is None or value == "" or value == []:
                missing_fields.append(field)
        
        if missing_fields:
            return ValidationResult(
                data_id=record.id,
                rule_name=rule.rule_name,
                is_valid=False,
                severity=rule.severity,
                message=f"{rule.error_message} Missing fields: {', '.join(missing_fields)}",
                citation=rule.citation,
                suggested_fixes=rule.suggested_fixes
            )
        
        return None
    
    def precision_check(
        self, 
        value: float, 
        rule: ValidationRule, 
        data_id: UUID
    ) -> Optional[ValidationResult]:
        """
        Check if decimal precision is reasonable
        
        Args:
            value: Numeric value to check
            rule: Validation rule with max_decimal_places parameter
            data_id: ID of the data record
        
        Returns:
            ValidationResult if check fails, None if passes
        """
        max_decimals = rule.parameters.get("max_decimal_places", 2)
        
        # Count decimal places
        value_str = f"{value:.10f}".rstrip('0')
        if '.' in value_str:
            decimal_places = len(value_str.split('.')[1])
        else:
            decimal_places = 0
        
        if decimal_places > max_decimals:
            return ValidationResult(
                data_id=data_id,
                rule_name=rule.rule_name,
                is_valid=False,
                severity=rule.severity,
                message=f"{rule.error_message} Value has {decimal_places} decimal places, expected max {max_decimals}.",
                citation=rule.citation,
                suggested_fixes=rule.suggested_fixes,
                actual_value=value
            )
        
        return None
    
    def validate_batch(
        self, 
        records: List[NormalizedRecord], 
        industry: str
    ) -> Dict[UUID, List[ValidationResult]]:
        """
        Validate multiple records and include cross-record validations (outliers)
        
        Args:
            records: List of normalized records to validate
            industry: Industry category
        
        Returns:
            Dictionary mapping data_id to list of validation results
        """
        results: Dict[UUID, List[ValidationResult]] = {}
        
        # Individual record validations
        for record in records:
            record_results = self.validate_record(record, industry)
            if record_results:
                results[record.id] = record_results
        
        # Outlier detection (cross-record validation)
        outlier_rule = self._get_outlier_rule(industry)
        if outlier_rule and len(records) >= 3:
            values = [(r.id, r.value) for r in records]
            outlier_results = self.outlier_detection(values, outlier_rule)
            
            for outlier_result in outlier_results:
                if outlier_result.data_id not in results:
                    results[outlier_result.data_id] = []
                results[outlier_result.data_id].append(outlier_result)
        
        return results
    
    def _get_outlier_rule(self, industry: str) -> Optional[ValidationRule]:
        """Get the outlier detection rule if available"""
        # Check cross-industry rules for outlier detection
        cross_industry_rules = self.rules.get("cross_industry", {})
        for rule in cross_industry_rules.values():
            if rule.validation_type == "outlier":
                return rule
        return None
    
    def get_rules_summary(self) -> Dict[str, Any]:
        """Get summary of loaded validation rules"""
        summary = {
            "total_rules": sum(len(rules) for rules in self.rules.values()),
            "industries": list(self.rules.keys()),
            "rules_by_industry": {
                industry: len(rules) 
                for industry, rules in self.rules.items()
            },
            "validation_types": set()
        }
        
        for industry_rules in self.rules.values():
            for rule in industry_rules.values():
                summary["validation_types"].add(rule.validation_type)
        
        summary["validation_types"] = list(summary["validation_types"])
        return summary
