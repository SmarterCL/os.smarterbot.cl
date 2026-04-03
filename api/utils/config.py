import os
from pathlib import Path
class Settings:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    LOG_DIR = BASE_DIR / "logs"
    SERVICE_NAME = "smarter-food"
    SERVICE_VERSION = "1.0.0"
settings = Settings()
