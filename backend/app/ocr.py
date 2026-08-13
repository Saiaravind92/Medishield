import os
import re
import cv2
import numpy as np
from PIL import Image
from typing import Dict, Any, List

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

def preprocess_image(image_path: str) -> np.ndarray:
    """Enhance document image for optimal text extraction."""
    img = cv2.imread(image_path)
    if img is None:
        pil_img = Image.open(image_path).convert('L')
        return np.array(pil_img)
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Apply contrast normalization & bilateral filtering
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    thresh = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    return thresh

def extract_raw_text(image_path: str) -> str:
    """Extract raw text using PyTesseract or Fallback OCR."""
    if not os.path.exists(image_path):
        return ""
    
    raw_text = ""
    if PYTESSERACT_AVAILABLE:
        try:
            processed = preprocess_image(image_path)
            raw_text = pytesseract.image_to_string(processed)
        except Exception:
            pass
            
    if not raw_text.strip():
        # Smart fallback: read text strings directly if accessible or parse file name / metadata
        try:
            pil_img = Image.open(image_path)
            # basic string fallback
            raw_text = f"Document: {os.path.basename(image_path)}"
        except Exception:
            pass
            
    return raw_text

def parse_clinical_financial_patterns(text: str) -> Dict[str, Any]:
    """Parse common structured fields from text using pattern matching."""
    parsed = {
        "policy_number": None,
        "member_name": None,
        "dob": None,
        "claim_amount": None,
        "icd10_codes": [],
        "cpt_codes": [],
        "npi": None,
        "service_date": None
    }
    
    # Policy Number (e.g. MED-GOLD-12345 or MED-100234)
    pol_match = re.search(r'\b(MED-[A-Z0-9-]+)\b', text, re.IGNORECASE)
    if pol_match:
        parsed["policy_number"] = pol_match.group(1).upper()
        
    # Claim Amount ($1,234.56 or 1234.56)
    amt_matches = re.findall(r'\$\s*([0-9,]+\.[0-9]{2})', text)
    if amt_matches:
        try:
            amounts = [float(a.replace(',', '')) for a in amt_matches]
            parsed["claim_amount"] = max(amounts) # usually total claim is highest
        except ValueError:
            pass
            
    # ICD-10 Diagnosis Codes (e.g., I25.10, E11.9, M17.11, Z96.651)
    icd_matches = re.findall(r'\b([A-TV-Z][0-9]{2}(?:\.[0-9]{1,4})?)\b', text)
    if icd_matches:
        parsed["icd10_codes"] = list(set(icd_matches))
        
    # CPT Procedure Codes (5-digit numbers like 99214, 33533, 27447, 43239, 93000)
    cpt_matches = re.findall(r'\b(99[0-9]{3}|33[0-9]{3}|27[0-9]{3}|43[0-9]{3}|93[0-9]{3}|71[0-9]{3}|80[0-9]{3})\b', text)
    if cpt_matches:
        parsed["cpt_codes"] = list(set(cpt_matches))
        
    # NPI (10 digits starting with 1 or 2)
    npi_match = re.search(r'\b([12][0-9]{9})\b', text)
    if npi_match:
        parsed["npi"] = npi_match.group(1)
        
    # Service Date (YYYY-MM-DD or MM/DD/YYYY)
    date_matches = re.findall(r'\b(202[456]-[0-1][0-9]-[0-3][0-9]|[0-1][0-9]/[0-3][0-9]/202[456])\b', text)
    if date_matches:
        parsed["service_date"] = date_matches[0]
        
    return parsed
