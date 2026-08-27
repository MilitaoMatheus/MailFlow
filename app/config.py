import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "Newsletter & Email Manager")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8000")

    # Chaves de Criptografia e Sessão
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default-dev-secret-key-change-me-in-production-min32chars")
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "WUZ4bU41U2Q3Wld5d05NZEp5Tk10cUtUdzJmQnVzTmc=")

    # Banco de Dados
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./newsletter.db")

    # Configuração de envio
    DEFAULT_RATE_LIMIT_PER_SECOND: int = int(os.getenv("DEFAULT_RATE_LIMIT_PER_SECOND", "5"))
    MOCK_EMAIL_SENDING: bool = os.getenv("MOCK_EMAIL_SENDING", "False").lower() in ("true", "1", "t")
    EMAIL_PROVIDER_DEFAULT: str = os.getenv("EMAIL_PROVIDER_DEFAULT", "smtp")

    # Diretórios
    BASE_DIR: Path = BASE_DIR
    TEMPLATES_DIR: Path = BASE_DIR / "app" / "templates"
    STATIC_DIR: Path = BASE_DIR / "app" / "static"


settings = Settings()
