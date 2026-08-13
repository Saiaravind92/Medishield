import os
import re
import pdfplumber
from typing import List, Dict, Any, Optional
from backend.app.config import settings
from backend.app.models import PolicyClause

class PolicyVectorStore:
    def __init__(self, policies_dir: str = settings.POLICIES_DIR):
        self.policies_dir = policies_dir
        self.documents: List[Dict[str, Any]] = []
        self._is_indexed = False

    def _index_policies(self):
        """Parse policy PDFs into searchable section chunks with memory caching."""
        if self._is_indexed and self.documents:
            return

        self.documents = []
        if not os.path.exists(self.policies_dir):
            return

        for fname in os.listdir(self.policies_dir):
            if fname.endswith(".pdf"):
                fpath = os.path.join(self.policies_dir, fname)
                plan_name = "MediShield Gold Plan" if "gold" in fname.lower() else "MediShield Silver Plan"
                
                try:
                    with pdfplumber.open(fpath) as pdf:
                        full_text = ""
                        for page in pdf.pages:
                            text = page.extract_text() or ""
                            full_text += text + "\n"
                        
                        sections = re.split(r'\n(?=[0-9]+\.\s+|SECTION\s+[0-9]+|ARTICLE\s+[0-9]+)', full_text)
                        for idx, sec in enumerate(sections):
                            sec_clean = sec.strip()
                            if len(sec_clean) < 30:
                                continue
                            lines = sec_clean.split("\n")
                            title = lines[0] if lines else f"Section {idx+1}"
                            
                            self.documents.append({
                                "plan_name": plan_name,
                                "file_name": fname,
                                "section_id": f"{fname}_sec_{idx}",
                                "title": title[:100],
                                "text": sec_clean,
                                "text_lower": sec_clean.lower()
                            })
                except Exception as e:
                    print(f"Error parsing policy PDF {fname}: {e}")

        self._is_indexed = True

    def query_policy(self, query: str, plan_name: str = "MediShield Gold Plan", top_k: int = 3) -> List[PolicyClause]:
        """Query in-memory pre-indexed policy vector store (< 1ms execution)."""
        if not self._is_indexed:
            self._index_policies()

        query_terms = [t.lower() for t in re.findall(r'\w+', query) if len(t) > 2]
        cpt_match = re.search(r'\b([0-9]{5})\b', query)
        target_cpt = cpt_match.group(1) if cpt_match else None

        scored_clauses = []
        target_plan = plan_name.lower()

        for doc in self.documents:
            if target_plan not in doc["plan_name"].lower() and "gold" in doc["plan_name"].lower():
                continue
                
            text_lower = doc["text_lower"]
            score = 0.0

            if target_cpt and target_cpt in text_lower:
                score += 10.0

            for term in query_terms:
                if term in text_lower:
                    score += 1.5

            if score > 0:
                scored_clauses.append((score, doc))

        scored_clauses.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, doc in scored_clauses[:top_k]:
            results.append(PolicyClause(
                section=doc["title"],
                title=doc["title"],
                clause_text=doc["text"][:600] + ("..." if len(doc["text"]) > 600 else ""),
                relevance_score=round(min(1.0, score / 10.0), 2)
            ))
            
        return results

policy_vector_store = PolicyVectorStore()
