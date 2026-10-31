import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file if it exists
load_dotenv(BASE_DIR / ".env")

class Config:
    """Base application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production-decision-maker-2026")
    
    # Database URL formatting (Render provides 'postgres://', SQLAlchemy 1.4+ expects 'postgresql://')
    raw_db_url = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'instance' / 'decision_maker.db'}")
    if raw_db_url and raw_db_url.startswith("postgres://"):
        raw_db_url = raw_db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # MongoDB Atlas settings
    MONGO_URI = os.getenv("MONGO_URI", "")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "decision_maker")
    
    # AI Assistant Keys
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("AI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Admin Security
    ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "dm-admin-secret-token")
    
    # Rate Limiting
    RATELIMIT_DEFAULT = "120 per minute"
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_STRATEGY = "fixed-window"
    
    # Third-Party Weather API
    WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"
    EXTERNAL_API_TIMEOUT = 3.0

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    RATELIMIT_ENABLED = False
