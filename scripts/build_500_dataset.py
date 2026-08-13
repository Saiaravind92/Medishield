import os
import json
import random
from PIL import Image, ImageDraw, ImageFont

DATASET_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset"))
os.makedirs(DATASET_DIR, exist_ok=True)

CATEGORIES = [
    ("claim_forms", "claim", "CMS1500"),
    ("id_documents", "id", "ID_DOCUMENT"),
    ("discharge_summaries", "discharge", "DISCHARGE_SUMMARY"),
    ("prescriptions", "rx", "PRESCRIPTION"),
    ("policy_amendments", "amend", "POLICY_AMENDMENT"),
    ("unknown", "unknown", "UNKNOWN")
]

for cat, _, _ in CATEGORIES:
    os.makedirs(os.path.join(DATASET_DIR, cat), exist_ok=True)

meta_path = os.path.join(DATASET_DIR, "metadata.json")
existing_meta = []
if os.path.exists(meta_path):
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            existing_meta = json.load(f)
    except Exception:
        existing_meta = []

print(f"Existing metadata count: {len(existing_meta)}")

FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Linda", "William", "Elizabeth", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]

rng = random.Random(42)
new_meta = list(existing_meta)

def create_sample_img(file_path, title_text, doc_id):
    W, H = 800, 1000
    img = Image.new("RGB", (W, H), (252, 253, 255))
    d = ImageDraw.Draw(img)
    
    # Border
    d.rectangle([20, 20, W-20, H-20], outline=(40, 60, 100), width=3)
    # Header
    d.rectangle([30, 30, W-30, 110], fill=(20, 40, 90))
    d.text((50, 50), "MEDISHIELD HEALTHCARE SYSTEMS", fill=(255, 255, 255))
    d.text((50, 80), f"DOCUMENT TYPE: {title_text} | REF: {doc_id}", fill=(200, 220, 255))
    
    # Body simulated lines
    for y in range(150, H-100, 30):
        d.line([(50, y), (W-50, y)], fill=(220, 225, 235), width=1)
        if rng.random() > 0.4:
            d.rectangle([60, y-15, rng.randint(200, W-100), y-5], fill=(70, 80, 110))
            
    # Save image
    img.save(file_path, "PNG")

target_total = 500
current_count = len(new_meta)
doc_index = current_count + 1

while len(new_meta) < target_total:
    cat, prefix, doc_type_name = CATEGORIES[(doc_index - 1) % len(CATEGORIES)]
    pt_id = f"PT_{10000 + doc_index}"
    doc_id = f"{prefix}_{pt_id}"
    fname = f"{doc_id}.png"
    rel_file_path = os.path.join("dataset", cat, fname)
    abs_file_path = os.path.join(DATASET_DIR, cat, fname)
    
    if not os.path.exists(abs_file_path):
        create_sample_img(abs_file_path, doc_type_name, doc_id)
        
    p_name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    p_num = f"MED-GLD-{rng.randint(100000, 999999)}"
    
    meta_entry = {
        "doc_id": doc_id,
        "category": cat,
        "case_cluster_id": f"CLUS-{doc_index:04d}",
        "fraud_label": (doc_index % 11 == 0),
        "fraud_reason": "duplicate_claim" if (doc_index % 11 == 0) else None,
        "edge_flags": ["expiring_soon_id"] if (doc_index % 17 == 0) else [],
        "patient_id": pt_id,
        "patient_name": p_name,
        "policy_number": p_num,
        "blur_simulated": False,
        "file_path": rel_file_path
    }
    
    new_meta.append(meta_entry)
    doc_index += 1

with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(new_meta, f, indent=4, default=str)

print(f"Successfully updated {meta_path} to {len(new_meta)} records!")
