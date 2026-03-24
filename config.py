"""
Configurações globais da aplicação.
Todas as variáveis de ambiente devem ser definidas no arquivo .env
"""
import os
from pathlib import Path
from typing import Optional


class Settings:
    BASE_DIR: Path = Path(__file__).parent
    DASHBOARDS_DIR: Path = BASE_DIR / "dashboards"
    
    ENV: str = os.getenv("ENV", "production")
    DEBUG: bool = ENV.lower() == "development"
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8050"))
    
    DEFAULT_REFRESH_INTERVAL: int = int(os.getenv("DEFAULT_REFRESH_INTERVAL", "0"))
    
    @classmethod
    def is_production(cls) -> bool:
        return cls.ENV.lower() == "production"
    
    @classmethod
    def is_development(cls) -> bool:
        return cls.DEBUG


settings = Settings()
