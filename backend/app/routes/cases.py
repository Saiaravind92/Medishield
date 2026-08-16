import os
import shutil
import uuid
import time
from typing import List, Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import FileResponse
from backend.app.models import Case, HumanOverrideRequest, DecisionType, AuditEntry
from backend.app.storage import storage_manager
from backend.app.graph import pipeline_graph
from backend.app.ela import compute_ela_score
from backend.app.config import settings
from backend.app.guardrails import validate_uploaded_file

router = APIRouter(prefix="/cases", tags=["Cases"])

@router.get("", response_model=List[Case])
def list_cases(
    status: Optional[str] = Query("ALL"),
    doc_type: Optional[str] = Query("ALL"),
    search: Optional[str] = Query(None)
):
    return storage_manager.list_cases(status=status, doc_type=doc_type, search=search)

@router.get("/stats")
def get_stats():
    cases = storage_manager.list_cases()
    total = len(cases)
    approved = sum(1 for c in cases if c.status == DecisionType.APPROVE)
    rejected = sum(1 for c in cases if c.status == DecisionType.REJECT)
    escalated = sum(1 for c in cases if c.status == DecisionType.ESCALATE)
    processing = sum(1 for c in cases if c.status == DecisionType.PROCESSING)
    
    return {
        "total_cases": total,
        "approved_cases": approved,
        "rejected_cases": rejected,
        "escalated_cases": escalated,
        "processing_cases": processing
    }

@router.get("/{case_id}/image")
def get_case_image(case_id: str):
    case = storage_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        
    if os.path.exists(case.file_path):
        return FileResponse(case.file_path)
        
    for root, dirs, files in os.walk(settings.DATASET_DIR):
        if case.filename in files:
            return FileResponse(os.path.join(root, case.filename))
            
    raise HTTPException(status_code=404, detail="Case image file not found")

@router.get("/{case_id}/ela")
def get_case_ela_image(case_id: str):
    case = storage_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        
    fpath = case.file_path
    if not os.path.exists(fpath):
        for root, dirs, files in os.walk(settings.DATASET_DIR):
            if case.filename in files:
                fpath = os.path.join(root, case.filename)
                break
                
    if not os.path.exists(fpath):
        raise HTTPException(status_code=404, detail="Source image for ELA not found")
        
    ela_path = fpath + "_ela.jpg"
    if not os.path.exists(ela_path):
        _, _, ela_path = compute_ela_score(fpath)
        
    if os.path.exists(ela_path):
        return FileResponse(ela_path)
    return FileResponse(fpath)

@router.get("/{case_id}", response_model=Case)
def get_case(case_id: str):
    case = storage_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.post("/upload", response_model=Case)
async def upload_document(file: UploadFile = File(...)):
    file_bytes = await file.read()
    validate_uploaded_file(file, file_bytes=file_bytes)
    await file.seek(0)
    
    case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    filename = file.filename or "document"
    dest_path = os.path.join(settings.STORAGE_DIR, f"{case_id}_{filename}")
    
    with open(dest_path, "wb") as buffer:
        buffer.write(file_bytes)
        
    case = pipeline_graph.run_case_pipeline(case_id, dest_path)
    return case

@router.post("/ingest-dataset")
def ingest_dataset_batch(limit: int = Query(500, ge=1, le=1000)):
    dataset_dir = settings.DATASET_DIR
    if not os.path.exists(dataset_dir):
        raise HTTPException(status_code=404, detail="Dataset directory not found.")
        
    processed_count = 0
    ingested_cases = []
    
    all_files = []
    for root, dirs, files in os.walk(dataset_dir):
        if "policies" in root:
            continue
        for f in files:
            if f.endswith(('.png', '.jpg', '.jpeg', '.pdf')):
                all_files.append(os.path.join(root, f))
                
    all_files.sort()
    
    for fpath in all_files[:limit]:
        fname = os.path.basename(fpath)
        case_id = f"CASE-{uuid.uuid4().hex[:8].upper()}"
        dest_path = os.path.join(settings.STORAGE_DIR, f"{case_id}_{fname}")
        shutil.copy(fpath, dest_path)
        
        case = pipeline_graph.run_case_pipeline(case_id, dest_path)
        ingested_cases.append(case)
        processed_count += 1
        
    return {
        "status": "success",
        "processed_count": processed_count,
        "sample_cases": [c.case_id for c in ingested_cases[:5]]
    }

@router.post("/{case_id}/override", response_model=Case)
def override_case_decision(case_id: str, req: HumanOverrideRequest):
    case = storage_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
        
    case.human_override = True
    case.human_decision = req.decision
    case.human_notes = req.notes
    case.status = req.decision
    
    case.audit_trail.append(AuditEntry(
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        agent="HUMAN_OPERATOR",
        action="DECISION_OVERRIDE",
        details=f"Decision overridden to {req.decision.value}. Notes: {req.notes}"
    ))
    
    storage_manager.save_case(case)
    return case
