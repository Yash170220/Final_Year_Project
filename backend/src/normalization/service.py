"""Normalization service for ESG data."""

import logging
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

logger = logging.getLogger(__name__)


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
                MatchedIndicator.reviewed.is_(True)
            )
            .all()
        )

        if not matched_indicators:
            raise NormalizationError(f"No approved indicators found for upload {upload_id}")

        # Load uploaded data based on file type
        file_path = upload.file_path
        if file_path.endswith(".csv"):
            data_df = pl.read_csv(file_path)
        elif file_path.endswith((".xlsx", ".xls")):
            data_df = pl.read_excel(file_path)
        elif file_path.endswith(".parquet"):
            data_df = pl.read_parquet(file_path)
        else:
            raise NormalizationError(f"Unsupported file format: {file_path}")

        # Track statistics
        total_records = 0
        successfully_normalized = 0
        failed_normalization = 0
        unique_units = set()
        conversions_applied = {}
        errors = []

        try:
            # Process each matched indicator
            for indicator in matched_indicators:
                indicator_total = 0
                indicator_success = 0
                column_data = []
                
                try:
                    # Get column data
                    if indicator.original_header not in data_df.columns:
                        error_msg = f"Column '{indicator.original_header}' not found in data"
                        errors.append(error_msg)
                        logger.warning(error_msg)
                        continue

                    column_data = data_df[indicator.original_header].to_list()
                    indicator_total = len([v for v in column_data if isinstance(v, (int, float)) and v is not None])
                    
                    # Process indicator
                    records = self.process_indicator(
                        indicator.id,
                        indicator.original_header,
                        indicator.matched_indicator,
                        column_data
                    )

                    # Inject upload_id into record metadata for DB save
                    for rec in records:
                        rec.metadata["upload_id"] = upload_id

                    if records:
                        self.save_normalized_data(records)
                        indicator_success = len(records)
                        
                        # Track statistics
                        for record in records:
                            unique_units.add(record.original_unit)
                            conversion_key = f"{record.original_unit}->{record.normalized_unit}"
                            conversions_applied[conversion_key] = conversions_applied.get(conversion_key, 0) + 1
                    
                    successfully_normalized += indicator_success
                    total_records += indicator_total

                except Exception as e:
                    error_msg = f"Error processing {indicator.original_header}: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg, exc_info=True)
                    
                    # Rollback this indicator's transaction
                    self.db.rollback()
                    
                    # Update failure count - use indicator_total if set, otherwise estimate from column_data
                    if indicator_total > 0:
                        failed_normalization += indicator_total
                    elif column_data:
                        failed_normalization += len([v for v in column_data if isinstance(v, (int, float)) and v is not None])
                    
                    total_records += indicator_total if indicator_total > 0 else len(column_data) if column_data else 0

            # Create audit log
            self._create_audit_log(
                upload_id,
                f"Normalized {successfully_normalized}/{total_records} records"
            )

        except Exception as e:
            # Rollback entire transaction on critical failure
            self.db.rollback()
            logger.error(f"Critical error during normalization: {str(e)}", exc_info=True)
            raise NormalizationError(f"Normalization failed: {str(e)}") from e

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
                # Log individual value errors but continue processing
                logger.debug(f"Failed to normalize value {value} at index {idx}: {str(e)}")
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
        """Save normalized records to database with transaction.
        
        Args:
            records: List of NormalizedRecord objects
            
        Raises:
            Exception: If database operation fails (caller should rollback)
        """
        db_records = []
        for record in records:
            db_record = NormalizedData(
                upload_id=record.metadata.get("upload_id") if record.metadata else None,
                indicator_id=record.matched_indicator_id,
                original_value=record.original_value,
                original_unit=record.original_unit,
                normalized_value=record.normalized_value,
                normalized_unit=record.normalized_unit,
                conversion_factor=record.conversion_factor or 1.0,
                conversion_source=record.metadata.get("conversion_source", "detected") if record.metadata else "detected",
            )
            db_records.append(db_record)

        # Bulk insert with explicit transaction
        try:
            self.db.bulk_save_objects(db_records)
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to save normalized data: {str(e)}", exc_info=True)
            raise

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
        # Use joinedload to avoid N+1 queries
        from sqlalchemy.orm import joinedload

        query = (
            self.db.query(NormalizedData)
            .join(MatchedIndicator, NormalizedData.indicator_id == MatchedIndicator.id)
            .options(joinedload(NormalizedData.indicator))
            .filter(MatchedIndicator.upload_id == upload_id)
        )

        if indicator_name:
            query = query.filter(MatchedIndicator.matched_indicator == indicator_name)

        records = query.all()

        if not records:
            return pl.DataFrame()

        data = {
            'indicator': [r.indicator.matched_indicator for r in records],
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
                MatchedIndicator.reviewed.is_(True)
            )
            .all()
        )

        for indicator in matched_indicators:
            # Get unique units for this indicator
            units = (
                self.db.query(NormalizedData.original_unit)
                .filter(NormalizedData.indicator_id == indicator.id)
                .distinct()
                .all()
            )

            unit_list = [u[0] for u in units]
            if len(unit_list) > 1:
                conflicts[indicator.matched_indicator] = unit_list

        return conflicts

    def get_comprehensive_results(
        self,
        upload_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> Optional[Dict]:
        """Get all normalization data for an upload in one call.

        Returns a dict matching NormalizationResponse or None if upload missing.
        """
        upload = self.db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            return None

        all_records = (
            self.db.query(NormalizedData)
            .filter(NormalizedData.upload_id == upload_id)
            .all()
        )

        total = len(all_records)
        failed = 0
        status = "completed" if total > 0 else "pending"

        # Build conversions map keyed by (indicator, from, to)
        conversions_map: Dict[str, Dict] = {}
        for r in all_records:
            indicator_name = r.indicator.matched_indicator if r.indicator else "Unknown"
            key = f"{indicator_name}|{r.original_unit}|{r.normalized_unit}"
            if key not in conversions_map:
                conversions_map[key] = {
                    "indicator": indicator_name,
                    "from_unit": r.original_unit,
                    "to_unit": r.normalized_unit,
                    "conversion_factor": r.conversion_factor,
                    "conversion_source": r.conversion_source or "Unknown",
                    "record_count": 0,
                }
            conversions_map[key]["record_count"] += 1

        # Errors: matched indicators with zero normalized rows
        matched = (
            self.db.query(MatchedIndicator)
            .filter(MatchedIndicator.upload_id == upload_id)
            .all()
        )
        normalised_indicator_ids = {r.indicator_id for r in all_records}
        errors = []
        for mi in matched:
            if mi.id not in normalised_indicator_ids:
                failed += 1
                errors.append({
                    "indicator": mi.matched_indicator,
                    "issue": "Unit not detected",
                    "suggestion": "Add unit to header or review manually",
                })

        rate = total / (total + failed) if (total + failed) > 0 else 0.0

        # Data sample (paginated)
        sample_records = (
            self.db.query(NormalizedData)
            .filter(NormalizedData.upload_id == upload_id)
            .order_by(NormalizedData.id)
            .offset(offset)
            .limit(limit)
            .all()
        )
        data_sample = []
        for r in sample_records:
            indicator_name = r.indicator.matched_indicator if r.indicator else "Unknown"
            data_sample.append({
                "data_id": r.id,
                "indicator": indicator_name,
                "original_value": r.original_value,
                "original_unit": r.original_unit,
                "normalized_value": r.normalized_value,
                "normalized_unit": r.normalized_unit,
            })

        return {
            "upload_id": upload_id,
            "status": status,
            "summary": {
                "total_records": total,
                "successfully_normalized": total,
                "failed_normalization": failed,
                "normalization_rate": round(rate, 4),
            },
            "conversions": list(conversions_map.values()),
            "errors": errors,
            "data_sample": data_sample,
        }

    def _create_audit_log(self, upload_id: UUID, message: str) -> None:
        """Create audit log entry.
        
        Args:
            upload_id: Upload UUID
            message: Audit message
        """
        try:
            audit = AuditLog(
                entity_id=upload_id,
                entity_type="upload",
                action=AuditAction.NORMALIZE,
                actor="system",
                changes={"message": message},
                timestamp=datetime.now(timezone.utc)
            )
            self.db.add(audit)
            self.db.commit()
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}", exc_info=True)
            self.db.rollback()
            # Don't raise - audit log failure shouldn't break normalization
