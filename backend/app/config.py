import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables from .env file
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
env_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path, override=True)

class Settings(BaseModel):
    PROJECT_NAME: str = "MediShield AI Claim Intake System"
    API_V1_STR: str = "/api/v1"
    
    BASE_DIR: str = BASE_DIR
    DATASET_DIR: str = os.path.join(BASE_DIR, "dataset")
    METADATA_FILE: str = os.path.join(DATASET_DIR, "metadata.json")
    STORAGE_DIR: str = os.path.join(BASE_DIR, "storage")
    DB_PATH: str = os.path.join(STORAGE_DIR, "medishield.db")
    POLICIES_DIR: str = os.path.join(DATASET_DIR, "policies")
    
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    VECTOR_DB_DIR: str = os.path.join(STORAGE_DIR, "chroma_db")

settings = Settings()
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
