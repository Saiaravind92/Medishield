import os
import json
from collections import Counter

meta_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset", "metadata.json"))
summary_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dataset_summary.md"))

with open(meta_path, "r", encoding="utf-8") as f:
    metadata = json.load(f)

cat_counts = Counter(m["category"] for m in metadata)
total_docs = len(metadata)
fraud_docs = sum(1 for m in metadata if m.get("fraud_label"))

lines = [
    "# MediShield Synthetic Dataset Summary",
    "",
    f"**Total documents:** {total_docs}  |  **Categories:** {len(cat_counts)}  |  **Fraud cases:** {fraud_docs}",
    "",
    "---",
    "",
    "## 1. Document Counts per Category",
    "",
    "| Category | Count |",
    "|---|---|",
]

for cat, cnt in sorted(cat_counts.items()):
    lines.append(f"| {cat:<24} | {cnt:>5} |")

lines.extend([
    f"| **TOTAL** | **{total_docs:>5}** |",
    "",
    "---",
    "",
    "## 2. Ingestion & Evaluation Ready",
    f"The dataset contains {total_docs} complete records with metadata entries for end-to-end multi-agent ingestion, OCR text parsing, KYC verification, policy RAG coverage lookup, and fraud scoring.",
    ""
])

with open(summary_path, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"Updated {summary_path} with {total_docs} records summary!")
