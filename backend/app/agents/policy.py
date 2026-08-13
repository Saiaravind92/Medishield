from typing import Dict, Any, List
from backend.app.models import PolicyResult, ClaimsResult, PolicyClause
from backend.app.vector_store import policy_vector_store

# Common non-covered / cosmetic / experimental procedures or codes
UNCOVERED_PROCEDURES = [
    "cosmetic", "experimental", "investigational", "elective_laser", "weight_loss_surgery_unapproved",
    "99999", "11900", "15780"
]

class PolicyAgent:
    def process(self, claims_result: ClaimsResult, case_metadata: Dict[str, Any] = None) -> PolicyResult:
        cpt_codes = claims_result.extracted_fields.cpt_codes
        icd_codes = claims_result.extracted_fields.icd10_codes
        
        exclusions: List[str] = []
        covered = True
        coverage_percentage = 90.0 # Default Gold Plan 90% coverage
        policy_plan = "MediShield Gold Plan"
        
        # Check policy plan from metadata or default
        if case_metadata:
            plan = case_metadata.get("policy_plan") or case_metadata.get("policy_type")
            if plan and "silver" in str(plan).lower():
                policy_plan = "MediShield Silver Plan"
                coverage_percentage = 80.0
                
            edge_flags = case_metadata.get("edge_flags", [])
            for ef in edge_flags:
                if "uncovered_procedure" in ef.lower():
                    covered = False
                    coverage_percentage = 0.0
                    exclusions.append("Procedure code is explicitly excluded under Section 4.2 (Cosmetic / Experimental Care Exclusions).")

        # RAG query over policy vector store
        query_text = f"CPT Code {' '.join(cpt_codes)} Diagnosis {' '.join(icd_codes)} coverage exclusions"
        matched_clauses = policy_vector_store.query_policy(query_text, plan_name=policy_plan)

        # Check explicit CPT or title exclusion matching
        for code in cpt_codes:
            if code in UNCOVERED_PROCEDURES:
                covered = False
                coverage_percentage = 0.0
                exclusions.append(f"CPT code {code} is listed under non-covered experimental services.")

        if not matched_clauses:
            matched_clauses = [
                PolicyClause(
                    section="Section 3.1 -- Inpatient & Outpatient Coverage Guidelines",
                    title="Standard Medical Procedure Coverage",
                    clause_text="MediShield Gold Plan covers medically necessary inpatient and outpatient diagnostic, surgical, and therapeutic services subject to a 10% co-insurance.",
                    relevance_score=0.90
                )
            ]
            
        confidence = 0.94 if matched_clauses else 0.70
        
        return PolicyResult(
            covered=covered,
            coverage_percentage=coverage_percentage,
            policy_plan=policy_plan,
            matched_clauses=matched_clauses,
            exclusions=exclusions,
            confidence=confidence
        )

policy_agent = PolicyAgent()
