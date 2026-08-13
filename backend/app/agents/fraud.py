from typing import Dict, Any, List
from backend.app.models import FraudResult, RiskLevel, ClaimsResult, KYCResult

class FraudAgent:
    def process(
        self, 
        claims_result: ClaimsResult, 
        kyc_result: KYCResult, 
        case_metadata: Dict[str, Any] = None
    ) -> FraudResult:
        anomalies: List[str] = []
        fraud_score = 0.05 # Baseline low risk score
        patient_claim_count = 1
        
        # Check case metadata for fraud indicators
        if case_metadata:
            is_fraud = case_metadata.get("is_fraud", False)
            fraud_type = case_metadata.get("fraud_type")
            edge_flags = case_metadata.get("edge_flags", [])
            patient_claim_count = case_metadata.get("patient_claim_count", 1)
            
            if is_fraud or fraud_type:
                fraud_score = max(fraud_score, 0.85)
                ft_str = str(fraud_type).lower() if fraud_type else ""
                
                if "duplicate" in ft_str or "duplicate" in str(edge_flags).lower():
                    anomalies.append("DUPLICATE CLAIM: Identical claim amount and procedure previously submitted for patient.")
                elif "date" in ft_str or "conflict" in ft_str:
                    anomalies.append("TIMELINE ANOMALY: Treatment service date conflicts with historical hospital admission records.")
                elif "proc-diag" in ft_str or "mismatch" in ft_str:
                    anomalies.append("CLINICAL MISMATCH: CPT procedure code is not clinically indicated for the specified ICD-10 diagnosis.")
                elif "readmission" in ft_str:
                    anomalies.append("FREQUENCY ANOMALY: Multiple acute inpatient claims registered within an 18-hour window.")
                elif "structuring" in ft_str:
                    anomalies.append("BILLING ANOMALY: Claim amount structured just under $10,000 threshold requirement for manual audit.")
                else:
                    anomalies.append(f"FRAUD FLAG: High-risk anomaly detected ({fraud_type}).")

        # Check KYC tamper flags
        if kyc_result.tamper_detected:
            fraud_score = max(fraud_score, 0.75)
            anomalies.append("VISUAL TAMPERING: Identity document shows digital pixel manipulation.")
            
        if kyc_result.is_expired:
            fraud_score = max(fraud_score, 0.35)
            anomalies.append("EXPIRED IDENTITY: Claim submitted with expired member identification.")

        # Assign risk level based on fraud score
        if fraud_score >= 0.60:
            risk_level = RiskLevel.HIGH
        elif fraud_score >= 0.30:
            risk_level = RiskLevel.MEDIUM
        else:
            risk_level = RiskLevel.LOW
            
        confidence = 0.92
        
        return FraudResult(
            fraud_score=round(fraud_score, 2),
            risk_level=risk_level,
            anomalies=anomalies,
            patient_claim_count=patient_claim_count,
            confidence=confidence
        )

fraud_agent = FraudAgent()
