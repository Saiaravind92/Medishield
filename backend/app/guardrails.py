import re
import os
from typing import Dict, Any, Tuple
from fastapi import HTTPException, UploadFile
from backend.app.models import DocumentType, DecisionType

# Allowed file extension whitelist for security
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".tiff"}
MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB limit

# Prompt injection signatures to block in OCR text / metadata
PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+all\s+previous\s+instructions",
    r"system\s+prompt\s+override",
    r"you\s+are\s+now\s+a\s+helpful\s+assistant\s+that\s+approves",
    r"bypass\s+verification",
    r"override\s+decision\s*=\s*approve",
    r"<script>",
    r"javascript:",
]

def validate_uploaded_file(file: UploadFile, file_bytes: bytes = None) -> Tuple[bool, str]:
    """
    Input file security guardrail: Checks extension, size limits, and sanitizes filename.
    """
    filename = file.filename or "unnamed_document"
    ext = os.path.splitext(filename)[1].lower()
    
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Security Guardrail: File type '{ext}' is not permitted. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )
        
    if file_bytes and len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Security Guardrail: File size exceeds maximum limit of 15MB (Size: {len(file_bytes) / (1024*1024):.2f}MB)"
        )
        
    # Sanitize filename to prevent directory traversal
    clean_filename = re.sub(r"[^a-zA-Z0-9_.-]", "_", os.path.basename(filename))
    return True, clean_filename

def sanitize_and_inspect_text(text: str) -> Tuple[str, bool]:
    """
    Prompt injection & malicious payload guardrail: Detects adversarial jailbreaks or prompt injections in OCR text.
    """
    if not text:
        return "", False
        
    suspicious_flag = False
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            suspicious_flag = True
            text = re.sub(pattern, "[BLOCKED_INJECTION_ATTEMPT]", text, flags=re.IGNORECASE)
            
    return text, suspicious_flag

def validate_classifier_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Output guardrail for Classifier Agent responses: Enforces bounded confidence and valid doc types.
    """
    doc_type = data.get("doc_type", "UNKNOWN")
    try:
        data["doc_type"] = DocumentType(doc_type).value
    except ValueError:
        data["doc_type"] = DocumentType.UNKNOWN.value
        
    try:
        conf = float(data.get("confidence", 0.5))
        data["confidence"] = max(0.0, min(1.0, conf))
    except (ValueError, TypeError):
        data["confidence"] = 0.50
        
    return data

def validate_claims_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Output guardrail for Claims Agent responses: Validates extracted financial values and schema standards.
    """
    fields = data.get("extracted_fields", {})
    if isinstance(fields, dict):
        try:
            claim_amt = float(fields.get("claim_amount", 0.0))
            fields["claim_amount"] = max(0.0, claim_amt)
        except (ValueError, TypeError):
            fields["claim_amount"] = 0.0
            
        npi = str(fields.get("provider_npi", "")).strip()
        if npi and not re.match(r"^\d{10}$", npi):
            fields["provider_npi_valid"] = False
        else:
            fields["provider_npi_valid"] = True
            
        data["extracted_fields"] = fields

    data["schema_valid"] = bool(data.get("schema_valid", True))
    return data

def validate_fraud_output(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Output guardrail for Fraud Agent responses: Bounds fraud scores between [0.0, 1.0] and syncs risk levels.
    """
    try:
        score = float(data.get("fraud_score", 0.0))
        score = max(0.0, min(1.0, score))
        data["fraud_score"] = score
    except (ValueError, TypeError):
        data["fraud_score"] = 0.0
        
    if data["fraud_score"] >= 0.3:
        data["risk_level"] = "HIGH"
    elif data["fraud_score"] >= 0.15:
        data["risk_level"] = "MEDIUM"
    else:
        data["risk_level"] = "LOW"
        
    return data
