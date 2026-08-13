import os
import json
import time
from typing import Dict, Any, Optional, Callable
from backend.app.models import (
    Case, DecisionType, DocumentType, ClassifierResult, 
    KYCResult, ClaimsResult, PolicyResult, FraudResult, OrchestratorResult, AuditEntry
)
from backend.app.agents.classifier import classifier_agent
from backend.app.agents.kyc import kyc_agent
from backend.app.agents.claims import claims_agent
from backend.app.agents.policy import policy_agent
from backend.app.agents.fraud import fraud_agent
from backend.app.agents.orchestrator import orchestrator_agent
from backend.app.storage import storage_manager
from backend.app.config import settings

class PipelineGraph:
    def __init__(self, metadata_path: str = settings.METADATA_FILE):
        self.metadata_path = metadata_path
        self._metadata_cache: Dict[str, Dict[str, Any]] = {}
        self._load_metadata()

    def _load_metadata(self):
        if os.path.exists(self.metadata_path):
            try:
                with open(self.metadata_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for item in data:
                            fname = item.get("file_name") or item.get("filename")
                            if not fname and item.get("file_path"):
                                fname = os.path.basename(item["file_path"])
                            if fname:
                                self._metadata_cache[fname] = item
                    elif isinstance(data, dict):
                        self._metadata_cache = data
            except Exception as e:
                print(f"Error loading metadata.json: {e}")

    def run_case_pipeline(
        self, 
        case_id: str, 
        file_path: str, 
        progress_callback: Optional[Callable[[str, str, Dict[str, Any]], None]] = None
    ) -> Case:
        filename = os.path.basename(file_path)
        case_meta = self._metadata_cache.get(filename, {})

        case = Case(
            case_id=case_id,
            filename=filename,
            file_path=file_path,
            created_at=time.strftime("%Y-%m-%d %H:%M:%S"),
            status=DecisionType.PROCESSING
        )

        def emit_step(agent_name: str, status_msg: str, payload: Dict[str, Any] = None):
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            case.audit_trail.append(AuditEntry(
                timestamp=timestamp,
                agent=agent_name,
                action="EXECUTE",
                details=status_msg
            ))
            if progress_callback:
                progress_callback(agent_name, status_msg, payload or {})

        # Step 1: Document Ingestion
        emit_step("Ingestion API", f"Document {filename} received and queued for processing.")

        # Step 2: Classifier Agent
        emit_step("Classifier Agent", "Analyzing document layout and vision features...")
        classifier_res = classifier_agent.process(file_path, case_meta)
        case.classifier_result = classifier_res
        case.doc_type = classifier_res.doc_type
        emit_step("Classifier Agent", f"Classified as {classifier_res.doc_type.value} (Confidence: {int(classifier_res.confidence*100)}%)", classifier_res.model_dump())

        # Step 3: KYC Agent
        emit_step("KYC Agent", "Verifying member identity and performing ELA tamper analysis...")
        kyc_res = kyc_agent.process(file_path, case_meta)
        case.kyc_result = kyc_res
        if kyc_res.member_name:
            case.patient_name = kyc_res.member_name
        if kyc_res.policy_number:
            case.policy_number = kyc_res.policy_number
        emit_step("KYC Agent", f"KYC {'Passed' if kyc_res.kyc_passed else 'Failed'} (Tamper score: {kyc_res.ela_tamper_score:.2f})", kyc_res.model_dump())

        # Step 4: Claims Agent
        emit_step("Claims Agent", "Extracting financial and clinical diagnosis/procedure codes...")
        claims_res = claims_agent.process(file_path, case_meta, doc_type=classifier_res.doc_type)
        case.claims_result = claims_res
        if claims_res.extracted_fields.patient_name:
            case.patient_name = claims_res.extracted_fields.patient_name
        if claims_res.extracted_fields.policy_number:
            case.policy_number = claims_res.extracted_fields.policy_number
        emit_step("Claims Agent", f"Extracted Claim Amount: ${claims_res.extracted_fields.claim_amount or 0:,.2f} | CPT: {', '.join(claims_res.extracted_fields.cpt_codes)}", claims_res.model_dump())

        # Step 5: Policy RAG Agent
        emit_step("Policy RAG Agent", "Querying vector store for MediShield policy clauses...")
        policy_res = policy_agent.process(claims_res, case_meta)
        case.policy_result = policy_res
        emit_step("Policy RAG Agent", f"Coverage Check: {'Covered' if policy_res.covered else 'Excluded'} ({policy_res.coverage_percentage:.0f}% rate)", policy_res.model_dump())

        # Step 6: Fraud Detection Agent
        emit_step("Fraud Agent", "Cross-checking patient claim history and billing anomalies...")
        fraud_res = fraud_agent.process(claims_res, kyc_res, case_meta)
        case.fraud_result = fraud_res
        emit_step("Fraud Agent", f"Fraud Risk Level: {fraud_res.risk_level.value} (Score: {fraud_res.fraud_score:.2f})", fraud_res.model_dump())

        # Step 7: Orchestrator Agent
        emit_step("Orchestrator Agent", "Synthesizing multi-agent outputs and applying decision rules...")
        orch_res = orchestrator_agent.process(
            classifier_res, kyc_res, claims_res, policy_res, fraud_res, case_meta
        )
        case.orchestrator_result = orch_res
        case.status = orch_res.decision
        emit_step("Orchestrator Agent", f"FINAL DECISION: {orch_res.decision.value} (Confidence: {int(orch_res.confidence*100)}%)", orch_res.model_dump())

        # Persist case to storage database
        storage_manager.save_case(case)
        return case

pipeline_graph = PipelineGraph()
