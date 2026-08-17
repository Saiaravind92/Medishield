import json
import sqlite3
from typing import List, Optional
from backend.app.config import settings
from backend.app.models import Case, DecisionType, DocumentType

class StorageManager:
    def __init__(self, db_path: str = settings.DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        # Performance PRAGMAs for fast SQLite reads/writes
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS cases (
                    case_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    status TEXT NOT NULL,
                    patient_name TEXT,
                    policy_number TEXT,
                    doc_type TEXT,
                    case_json TEXT NOT NULL
                )
            """)
            # Speed Indexing for fast queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_doc_type ON cases(doc_type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_created_at ON cases(created_at DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_search ON cases(patient_name, policy_number, case_id);")
            conn.commit()

    def save_case(self, case: Case) -> Case:
        case_dict = case.model_dump()
        case_json = json.dumps(case_dict, default=str)
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO cases 
                (case_id, filename, file_path, created_at, status, patient_name, policy_number, doc_type, case_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                case.case_id,
                case.filename,
                case.file_path,
                case.created_at,
                case.status.value if isinstance(case.status, DecisionType) else str(case.status),
                case.patient_name,
                case.policy_number,
                case.doc_type.value if isinstance(case.doc_type, DocumentType) else str(case.doc_type),
                case_json
            ))
            conn.commit()
        return case

    def get_case(self, case_id: str) -> Optional[Case]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT case_json FROM cases WHERE case_id = ?", (case_id,)).fetchone()
            if row:
                data = json.loads(row["case_json"])
                return Case.model_validate(data)
        return None

    def list_cases(
        self, 
        status: Optional[str] = None, 
        doc_type: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Case]:
        query = "SELECT case_json FROM cases WHERE 1=1"
        params = []
        
        if status and status != "ALL":
            query += " AND status = ?"
            params.append(status)
        if doc_type and doc_type != "ALL":
            query += " AND doc_type = ?"
            params.append(doc_type)
        if search:
            query += " AND (patient_name LIKE ? OR policy_number LIKE ? OR case_id LIKE ? OR filename LIKE ? OR doc_type LIKE ? OR case_json LIKE ?)"
            s = f"%{search}%"
            params.extend([s, s, s, s, s, s])
            
        query += " ORDER BY created_at DESC"
        
        cases = []
        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            for r in rows:
                data = json.loads(r["case_json"])
                cases.append(Case.model_validate(data))
        return cases

    def delete_case(self, case_id: str) -> bool:
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM cases WHERE case_id = ?", (case_id,))
            conn.commit()
            return cur.rowcount > 0

storage_manager = StorageManager()
