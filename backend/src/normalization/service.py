"""Normalization service for ESG data."""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

import polars as pl
from sqlalchemy.orm import Session

from src.common.models import (
    MatchedIndicator,
    NormalizedData,
    Upload,
    AuditLog,
    AuditAction,
)
from src.normalization.normalizer import UnitNormalizer, UnitNotFoundError


class NormalizationError(Exception):
    """Raised when normalization fails."""
    pass


@dataclass
class NormalizedRecord:
    """Single normalized data record."""
    matched_indicator_id: UUID
    original_value: float
    original_unit: str
    normalized_value: float
    normalized_unit: str
    conversion_factor: Optional[float]
    row_index: int
    metadata: Dict


@dataclass
class NormalizationSummary:
    """Summary of normalization operation."""
    total_records: int
    successfully_normalized: int
    failed_normalization: int
    unique_units_detected: List[str]
    conversions_applied: Dict[str, int]
    errors: List[str]


class NormalizationService:
    """Service for normalizing ESG data to canonical units."""

    def __init__(self, normalizer: UnitNormalizer, db_session: Session):
        """Initialize normalization service.
        
        Args:
            normalizer: UnitNormalizer instance
            db_session: Database session
        """
        self.normalizer = normalizer
        self.db = db_session

    def normalize_data(self, upload_id: UUID) -> NormalizationSummary:
        """Normalize all matched indicators for an upload.
        
        Args:
            upload_id: Upload UUID
            
        Returns:
            NormalizationSummary with statistics
            
        Raises:
            NormalizationError: If upload not found or normalization fails
        """
        # Get upload
        upload = self.db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            raise NormalizationError(f"Upload {upload_id} not found")

        # Get approved matched indicators
        matched_indicators = (
            self.db.query(MatchedIndicator)
            .filter(
                MatchedIndicator.upload_id == upload_id,
                MatchedIndicator.approved.is_(True)
            )
            .all()
        )

        if not matched_indicators:
            raise NormalizationError(f"No approved indicators found for upload {upload_id}")

        # Load uploaded data
        data_df = pl.read_parquet(upload.file_path)

        # Track statistics
        total_records = 0
        successfully_normalized = 0
        failed_normalization = 0
        unique_units = set()
        conversions_applied = {}
        errors = []

        # Process each matched indicator
        for indicator in matched_indicators:
            try:
                # Get column data
                if indicator.matched_header not in data_df.columns:
                    errors.append(f"Column '{indicator.matched_header}' not found in data")
                    continue

                column_data = data_df[indicator.matched_header].to_list()
                
                # Process indicator
                records = self.process_indicator(
                    indicator.id,
                    indicator.matched_header,
                    indicator.canonical_indicator,
                    column_data
                )

                # Save records
                if records:
                    self.save_normalized_data(records)
                    successfully_normalized += len(records)
                    
                    # Track statistics
                    for record in records:
                        unique_units.add(record.original_unit)
                        conversion_key = f"{record.original_unit}→{record.normalized_unit}"
                        conversions_applied[conversion_key] = conversions_applied.get(conversion_key, 0) + 1
                
                total_records += len(column_data)

            except Exception as e:
                error_msg = f"Error processing {indicator.matched_header}: {str(e)}"
                errors.append(error_msg)
                failed_normalization += len(column_data) if column_data else 0

        # Create audit log
        self._create_audit_log(
            upload_id,
            f"Normalized {successfully_normalized}/{total_records} records"
        )

        return NormalizationSummary(
            total_records=total_records,
            successfully_normalized=successfully_normalized,
            failed_normalization=failed_normalization,
            unique_units_detected=list(unique_units),
            conversions_applied=conversions_applied,
            errors=errors
        )

    def process_indicator(
        self,
        indicator_id: UUID,
        header_name: str,
        canonical_indicator: str,
        data: List
    ) -> List[NormalizedRecord]:
        """Process and normalize data for a single indicator.
        
        Args:
            indicator_id: Matched indicator UUID
            header_name: Original header name
            canonical_indicator: Canonical indicator name
            data: List of values
            
        Returns:
            List of NormalizedRecord objects
        """
        # Filter numeric values and get sample
        numeric_values = [v for v in data if isinstance(v, (int, float)) and v is not None]
        if not numeric_values:
            return []

        # Detect unit from context
        detected_unit = self.detect_unit_from_context(header_name, numeric_values[:100])
        
        if not detected_unit:
            raise NormalizationError(
                f"Could not detect unit for '{header_name}'. Manual review required."
            )

        # Normalize each value
        records = []
        for idx, value in enumerate(data):
            if not isinstance(value, (int, float)) or value is None:
                continue

            try:
                result = self.normalizer.normalize(float(value), detected_unit)
                
                record = NormalizedRecord(
                    matched_indicator_id=indicator_id,
                    original_value=value,
                    original_unit=detected_unit,
                    normalized_value=result.normalized_value,
                    normalized_unit=result.normalized_unit,
                    conversion_factor=result.conversion_factor,
                    row_index=idx,
                    metadata={
                        "header_name": header_name,
                        "canonical_indicator": canonical_indicator,
                        "conversion_source": result.conversion_source,
                        "formula": result.formula
                    }
                )
                records.append(record)

            except Exception as e:
                # Skip individual value errors but continue processing
                continue

        return records

    def detect_unit_from_context(
        self,
        indicator_name: str,
        sample_values: List[float]
    ) -> Optional[str]:
        """Detect unit from indicator name and value patterns.
        
        Args:
            indicator_name: Name of the indicator/header
            sample_values: Sample of numeric values
            
        Returns:
            Detected unit string or None
        """
        # Try to extract unit from indicator name
        unit_from_name = self._extract_unit_from_text(indicator_name)
        if unit_from_name:
            return unit_from_name

        # Analyze value magnitudes for common patterns
        if not sample_values:
            return None

        avg_value = sum(sample_values) / len(sample_values)
        max_value = max(sample_values)

        # Energy patterns
        if any(keyword in indicator_name.lower() for keyword in ['energy', 'electricity', 'power']):
            if max_value > 100000:
                return 'kWh'
            elif max_value > 100:
                return 'MWh'
            elif max_value > 1:
                return 'GJ'

        # Emissions patterns
        if any(keyword in indicator_name.lower() for keyword in ['emission', 'co2', 'ghg', 'carbon']):
            if 'kg' in indicator_name.lower():
                return 'kg CO2e'
            elif max_value > 1000:
                return 'kg CO2e'
            else:
                return 'tonnes CO2e'

        # Water patterns
        if any(keyword in indicator_name.lower() for keyword in ['water', 'consumption']):
            if max_value > 10000:
                return 'liters'
            else:
                return 'm3'

        # Mass patterns
        if any(keyword in indicator_name.lower() for keyword in ['waste', 'material', 'mass', 'weight']):
            if max_value > 10000:
                return 'kg'
            else:
                return 'tonnes'

        return None

    def _extract_unit_from_text(self, text: str) -> Optional[str]:
        """Extract unit from text using regex patterns.
        
        Args:
            text: Text to search for units
            
        Returns:
            Detected unit or None
        """
        # Common unit patterns in parentheses or brackets
        patterns = [
            r'\(([^)]+)\)',  # (unit)
            r'\[([^\]]+)\]',  # [unit]
            r'\s+in\s+(\w+)',  # "in unit"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                potential_unit = match.group(1).strip()
                # Try to detect if it's a valid unit
                try:
                    unit, category = self.normalizer.detect_unit(potential_unit)
                    return unit
                except UnitNotFoundError:
                    continue

        return None

    def save_normalized_data(self, records: List[NormalizedRecord]) -> None:
        """Save normalized records to database.
        
        Args:
            records: List of NormalizedRecord objects
        """
        db_records = []
        for record in records:
            db_record = NormalizedData(
                matched_indicator_id=record.matched_indicator_id,
                original_value=record.original_value,
                original_unit=record.original_unit,
                normalized_value=record.normalized_value,
                normalized_unit=record.normalized_unit,
                conversion_factor=record.conversion_factor,
                row_index=record.row_index,
                metadata=record.metadata
            )
            db_records.append(db_record)

        # Bulk insert
        self.db.bulk_save_objects(db_records)
        self.db.commit()

    def get_normalized_data(
        self,
        upload_id: UUID,
        indicator_name: Optional[str] = None
    ) -> pl.DataFrame:
        """Retrieve normalized data for an upload.
        
        Args:
            upload_id: Upload UUID
            indicator_name: Optional filter by canonical indicator name
            
        Returns:
            Polars DataFrame with normalized data
        """
        query = (
            self.db.query(NormalizedData)
            .join(MatchedIndicator)
            .filter(MatchedIndicator.upload_id == upload_id)
        )

        if indicator_name:
            query = query.filter(MatchedIndicator.canonical_indicator == indicator_name)

        records = query.all()

        if not records:
            return pl.DataFrame()

        # Convert to DataFrame
        data = {
            'indicator': [r.matched_indicator.canonical_indicator for r in records],
            'original_value': [r.original_value for r in records],
            'original_unit': [r.original_unit for r in records],
            'normalized_value': [r.normalized_value for r in records],
            'normalized_unit': [r.normalized_unit for r in records],
            'row_index': [r.row_index for r in records],
        }

        return pl.DataFrame(data)

    def check_unit_conflicts(self, upload_id: UUID) -> Dict[str, List[str]]:
        """Check for conflicting units in the same indicator.
        
        Args:
            upload_id: Upload UUID
            
        Returns:
            Dictionary mapping indicator names to list of conflicting units
        """
        conflicts = {}

        matched_indicators = (
            self.db.query(MatchedIndicator)
            .filter(
                MatchedIndicator.upload_id == upload_id,
                MatchedIndicator.approved.is_(True)
            )
            .all()
        )

        for indicator in matched_indicators:
            # Get unique units for this indicator
            units = (
                self.db.query(NormalizedData.original_unit)
                .filter(NormalizedData.matched_indicator_id == indicator.id)
                .distinct()
                .all()
            )

            unit_list = [u[0] for u in units]
            if len(unit_list) > 1:
                conflicts[indicator.canonical_indicator] = unit_list

        return conflicts

    def _create_audit_log(self, upload_id: UUID, message: str) -> None:
        """Create audit log entry.
        
        Args:
            upload_id: Upload UUID
            message: Audit message
        """
        audit = AuditLog(
            upload_id=upload_id,
            action=AuditAction.NORMALIZE,
            actor="system",
            details={"message": message},
            timestamp=datetime.now(timezone.utc)
        )
        self.db.add(audit)
        self.db.commit()
