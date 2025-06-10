# config.py
from dataclasses import dataclass, field
import os

@dataclass
class DBConfig:
    host: str = os.getenv("HANA_HOST", "saphamultifazendas")
    port: int = int(os.getenv("HANA_PORT", 30015))
    user: str = os.getenv("HANA_USER", "B1ADMIN")
    password: str = os.getenv("HANA_PASSWORD", "#xGCba!6e0YvK7*")

@dataclass
class SMTPConfig:
    server: str = os.getenv("SMTP_SERVER", "smtp.office365.com")
    port: int = int(os.getenv("SMTP_PORT", 587))
    user: str = os.getenv("SMTP_USER", "GIPBOT@trustagrocompany.com")
    password: str = os.getenv("SMTP_PASSWORD", "Trust@234")
    test_mode: bool = os.getenv("EMAIL_TEST_MODE", "false").lower() == "true"
    test_recipient: str = os.getenv(
        "EMAIL_TEST_RECIPIENT",
        "bernardo.kropiwiec@trustagrocompany.com",
    )

@dataclass
class SLConfig:
    base_url: str = os.getenv(
        "SL_BASE_URL",
        "https://saphamultifazendas:50000/b1s/v1",
    )
    user: str = os.getenv("SL_USER", "manager")
    password: str = os.getenv("SL_PASSWORD", "B1@admin")
    company_db: str = os.getenv("SL_COMPANY_DB", "SBOTRUSTAGRO")

@dataclass
class Settings:
    db:   DBConfig   = field(default_factory=DBConfig)
    smtp: SMTPConfig = field(default_factory=SMTPConfig)
    sl:   SLConfig   = field(default_factory=SLConfig)

# instância singleton que o resto do código importa
settings = Settings()
