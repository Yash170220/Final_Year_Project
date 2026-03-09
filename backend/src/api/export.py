"""API endpoints for report export."""

from pathlib import Path
from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from src.reporting.generator import ReportGenerator

router = APIRouter(prefix="/api/v1/export", tags=["export"])

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "data" / "templates"
generator = ReportGenerator(str(TEMPLATES_DIR))


@router.post("/{upload_id}")
async def export_reports(
    upload_id: UUID,
    format: str = Query("docx", regex="^(docx|pdf|excel)$"),
    report_types: List[str] = Query(["brsr"], description="Report types to generate")
):
    """Export reports in DOCX, PDF, or Excel format.
    
    Args:
        upload_id: Upload UUID
        format: Output format (docx, pdf, or excel)
        report_types: Types of reports to generate
        
    Returns:
        List of generated report paths
    """
    try:
        # Generate Excel for BRSR if requested
        if format == "excel" and "brsr" in report_types:
            excel_path = generator.generate_brsr_excel(
                upload_id=upload_id,
                company_info={"name": "Company", "cin": "CIN123"},
                normalized_data=[]
            )
            return {
                "upload_id": str(upload_id),
                "format": "excel",
                "reports": [{"type": "brsr", "format": "excel", "filepath": excel_path}]
            }
        
        # Generate DOCX reports
        reports = generator.generate_reports(
            upload_id=upload_id,
            data={},
            output_dir=f"data/exports/{upload_id}",
            formats=report_types
        )
        
        # Convert to PDF if requested
        if format == "pdf":
            for report in reports:
                try:
                    pdf_path = generator.convert_to_pdf(report['filepath'])
                    report['pdf_filepath'] = pdf_path
                    report['format'] = 'pdf'
                except Exception as e:
                    report['pdf_error'] = str(e)
        
        return {
            "upload_id": str(upload_id),
            "format": format,
            "reports": reports
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")
