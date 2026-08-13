from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

class DocumentType(str, Enum):
    CLAIM_FORM = "CLAIM_FORM"
    ID_DOCUMENT = "ID_DOCUMENT"
    DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY"
    PRESCRIPTION = "PRESCRIPTION"
    POLICY_AMENDMENT = "POLICY_AMENDMENT"
    UNKNOWN = "UNKNOWN"

class DecisionType(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    ESCALATE = "ESCALATE"
    PROCESSING = "PROCESSING"

class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class ClassifierResult(BaseModel):
    doc_type: DocumentType = DocumentType.UNKNOWN
    confidence: float = 0.0
    routing_tags: List[str] = []
    reasoning: str = ""

class KYCResult(BaseModel):
    kyc_passed: bool = False
    member_id: Optional[str] = None
    member_name: Optional[str] = None
    dob: Optional[str] = None
    policy_number: Optional[str] = None
    id_expiry: Optional[str] = None
    is_expired: bool = False
    ela_tamper_score: float = 0.0
    tamper_detected: bool = False
    flags: List[str] = []
    confidence: float = 0.0

class ExtractedClaimsFields(BaseModel):
    claim_amount: Optional[float] = None
    icd10_codes: List[str] = []
    cpt_codes: List[str] = []
    provider_npi: Optional[str] = None
    provider_name: Optional[str] = None
    service_date: Optional[str] = None
    patient_name: Optional[str] = None
    policy_number: Optional[str] = None

class ClaimsResult(BaseModel):
    extracted_fields: ExtractedClaimsFields = Field(default_factory=ExtractedClaimsFields)
    schema_valid: bool = False
    validation_errors: List[str] = []
    confidence: float = 0.0

class PolicyClause(BaseModel):
    section: str
    title: str
    clause_text: str
    relevance_score: float = 0.0

class PolicyResult(BaseModel):
    covered: bool = False
    coverage_percentage: float = 0.0
    policy_plan: str = "MediShield Gold Plan"
    matched_clauses: List[PolicyClause] = []
    exclusions: List[str] = []
    confidence: float = 0.0

class FraudResult(BaseModel):
    fraud_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    anomalies: List[str] = []
    patient_claim_count: int = 1
    confidence: float = 0.0

class OrchestratorResult(BaseModel):
    decision: DecisionType = DecisionType.PROCESSING
    confidence: float = 0.0
    justification: str = ""
    agent_summaries: Dict[str, str] = {}

class AuditEntry(BaseModel):
    timestamp: str
    agent: str
    action: str
    details: str

class Case(BaseModel):
    model_config = ConfigDict(extra="ignore")
    case_id: str
    filename: str
    file_path: str
    created_at: str
    status: DecisionType = DecisionType.PROCESSING
    patient_name: Optional[str] = "Unknown Patient"
    policy_number: Optional[str] = "MED-UNKNOWN"
    doc_type: DocumentType = DocumentType.UNKNOWN
    
    classifier_result: Optional[ClassifierResult] = None
    kyc_result: Optional[KYCResult] = None
    claims_result: Optional[ClaimsResult] = None
    policy_result: Optional[PolicyResult] = None
    fraud_result: Optional[FraudResult] = None
    orchestrator_result: Optional[OrchestratorResult] = None
    
    human_override: bool = False
    human_decision: Optional[DecisionType] = None
    human_notes: Optional[str] = None
    audit_trail: List[AuditEntry] = []

class HumanOverrideRequest(BaseModel):
    decision: DecisionType
    notes: str
