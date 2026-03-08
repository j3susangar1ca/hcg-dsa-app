from pydantic_settings import BaseSettings
from pydantic import ValidationError
from pathlib import Path
import sys

class Settings(BaseSettings):
    """Configuración tipada y validada desde variables de entorno."""
    gemini_api_key: str
    db_url: str = "sqlite:///cadido_database.db"
    network_base_path: Path = Path(r"\\10.2.1.92\FAA_divserv_admvos\CORRESPONDENCIA")
    default_subserie: str = "CORRESPONDENCIA_GENERAL"
    timezone: str = "America/Mexico_City"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

try:
    settings = Settings()
except ValidationError as e:
    print(f"Error de configuración: {e}")
    sys.exit(1)
