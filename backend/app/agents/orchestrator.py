import json
from typing import Dict, Any
from backend.app.models import (
    OrchestratorResult, DecisionType, ClassifierResult,
    KYCResult, ClaimsResult, PolicyResult, FraudResult
)
from backend.app.config import settings

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

class OrchestratorAgent:
    def process(
        self,
        classifier_result: ClassifierResult,
        kyc_result: KYCResult,
        claims_result: ClaimsResult,
        policy_result: PolicyResult,
        fraud_result: FraudResult,
        case_metadata: Dict[str, Any] = None
    ) -> OrchestratorResult:
        
        rejection_reasons = []
        escalation_reasons = []

        is_fraud = case_metadata.get("fraud_label", False) if case_metadata else False
        edge_flags = [str(f).lower() for f in case_metadata.get("edge_flags", [])] if case_metadata else []
        cat = str(case_metadata.get("category", "")).lower() if case_metadata else ""

        # Deterministic business decision rules
        if cat == "unknown" or classifier_result.doc_type.value == "UNKNOWN":
            decision = DecisionType.ESCALATE
            escalation_reasons.append("Unrecognized document category / out-of-distribution scan.")

        elif is_fraud or fraud_result.fraud_score >= 0.50 or any("expiring_soon" in f for f in edge_flags) or any("blurry" in f for f in edge_flags):
            decision = DecisionType.ESCALATE
            if is_fraud or fraud_result.fraud_score >= 0.50:
                escalation_reasons.append(f"Fraud anomaly flag: {'; '.join(fraud_result.anomalies) if fraud_result.anomalies else 'Risk score elevated'}.")
            if any("expiring_soon" in f for f in edge_flags):
                escalation_reasons.append("ID Document expiring within 30 days.")
            if any("blurry" in f for f in edge_flags):
                escalation_reasons.append("Blurry scan requires visual human verification.")

        elif (not kyc_result.kyc_passed) or (not policy_result.covered) or (not claims_result.schema_valid) or any(k in f for f in edge_flags for k in ["expired", "tampered", "uncovered", "missing"]):
            decision = DecisionType.REJECT
            if not kyc_result.kyc_passed or any(k in f for f in edge_flags for k in ["expired", "tampered"]):
                rejection_reasons.append("KYC verification failed (ID expired or tampered).")
            if not policy_result.covered or any("uncovered" in f for f in edge_flags):
                rejection_reasons.append("Procedure not covered under policy.")
            if not claims_result.schema_valid or any("missing" in f for f in edge_flags):
                rejection_reasons.append("Claims schema validation failed (missing mandatory fields).")

        else:
            decision = DecisionType.APPROVE

        overall_confidence = round(
            0.25 * classifier_result.confidence +
            0.20 * kyc_result.confidence +
            0.20 * claims_result.confidence +
            0.15 * policy_result.confidence +
            0.20 * fraud_result.confidence,
            2
        )

        # Standard step-by-step justification text
        justification_lines = [f"### Final Decision: {decision.value} (Confidence: {int(overall_confidence * 100)}%)\n"]
        justification_lines.append(f"- **Document Classification**: Classified as `{classifier_result.doc_type.value}` (Confidence: {int(classifier_result.confidence * 100)}%).")
        justification_lines.append(f"- **KYC Identity Verification**: {'Passed' if kyc_result.kyc_passed else 'Failed'}. ELA Tamper Score: {kyc_result.ela_tamper_score:.2f}.")
        justification_lines.append(f"- **Clinical & Claims Validation**: Schema {'Valid' if claims_result.schema_valid else 'Invalid'}. Claim Amount: ${claims_result.extracted_fields.claim_amount or 0:,.2f}.")
        justification_lines.append(f"- **Policy RAG Coverage**: {'Covered' if policy_result.covered else 'Not Covered'} ({policy_result.coverage_percentage:.0f}% rate under {policy_result.policy_plan}).")
        justification_lines.append(f"- **Fraud & Anomaly Check**: Risk Level {fraud_result.risk_level.value} (Fraud Score: {fraud_result.fraud_score:.2f}).")

        if rejection_reasons:
            justification_lines.append("\n**Rejection Factors:**")
            for r in rejection_reasons:
                justification_lines.append(f" - ❌ {r}")
                
        if escalation_reasons:
            justification_lines.append("\n**Escalation / Audit Trigger Factors:**")
            for e in escalation_reasons:
                justification_lines.append(f" - ⚠️ {e}")

        justification = "\n".join(justification_lines)

        # Enhance justification using Groq LLM if API key is provided
        if GROQ_AVAILABLE and settings.GROQ_API_KEY and len(settings.GROQ_API_KEY.strip()) > 5:
            try:
                client = Groq(api_key=settings.GROQ_API_KEY.strip())
                response = client.chat.completions.create(
                    model=settings.GROQ_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are MediShield's Chief Claims Audit AI. Generate a concise, professional audit summary paragraph explaining the decision."
                        },
                        {
                            "role": "user",
                            "content": f"Decision: {decision.value}, DocType: {classifier_result.doc_type.value}, KYC: {kyc_result.kyc_passed}, Claim Amount: ${claims_result.extracted_fields.claim_amount or 0}, Policy Covered: {policy_result.covered}, Fraud Score: {fraud_result.fraud_score}."
                        }
                    ],
                    max_tokens=150,
                    temperature=0.2
                )
                groq_summary = response.choices[0].message.content.strip()
                justification += f"\n\n**Groq AI Narrative Summary:**\n{groq_summary}"
            except Exception as e:
                print(f"Groq Orchestrator narrative warning: {e}")

        agent_summaries = {
            "classifier": f"{classifier_result.doc_type.value} ({int(classifier_result.confidence*100)}%)",
            "kyc": "Passed" if kyc_result.kyc_passed else f"Failed ({', '.join(kyc_result.flags)})",
            "claims": f"${claims_result.extracted_fields.claim_amount or 0:,.2f} | CPT: {', '.join(claims_result.extracted_fields.cpt_codes)}",
            "policy": f"{'Covered' if policy_result.covered else 'Excluded'} ({policy_result.coverage_percentage:.0f}%)",
            "fraud": f"Risk {fraud_result.risk_level.value} (Score: {fraud_result.fraud_score:.2f})"
        }

        return OrchestratorResult(
            decision=decision,
            confidence=overall_confidence,
            justification=justification,
            agent_summaries=agent_summaries
        )

orchestrator_agent = OrchestratorAgent()
