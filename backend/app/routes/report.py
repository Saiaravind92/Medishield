import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from backend.app.storage import storage_manager
from backend.app.pdf_report import generate_case_pdf_report
from backend.app.config import settings

router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/{case_id}/download")
def download_case_report(case_id: str):
    case = storage_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    pdf_filename = f"MediShield_Audit_Report_{case_id}.pdf"
    output_pdf_path = os.path.join(settings.STORAGE_DIR, pdf_filename)
    
    generate_case_pdf_report(case, output_pdf_path)
    
    if not os.path.exists(output_pdf_path):
        raise HTTPException(status_code=500, detail="Failed to generate PDF report")
        
    return FileResponse(
        path=output_pdf_path,
        filename=pdf_filename,
        media_type="application/pdf"
    )
