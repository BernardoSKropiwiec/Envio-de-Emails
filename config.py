# config.py
from dataclasses import dataclass, field
import os

@dataclass
class DBConfig:
    host: str = os.getenv("HANA_HOST", "s--")
    port: int = int(os.getenv("HANA_PORT", 30015))
    user: str = os.getenv("HANA_USER", "--")
    password: str = os.getenv("HANA_PASSWORD", "--")

@dataclass
class SMTPConfig:
    server: str = os.getenv("SMTP_SERVER", "smtp.office365.com")
    port: int = int(os.getenv("SMTP_PORT", 587))
    user: str = os.getenv("SMTP_USER", "--")
    password: str = os.getenv("SMTP_PASSWORD", "--")
    test_mode: bool = os.getenv("EMAIL_TEST_MODE", "false").lower() == "true"
    test_recipient: str = os.getenv(
        "EMAIL_TEST_RECIPIENT",
        "--",
    )

@dataclass
class SLConfig:
    base_url: str = os.getenv(
        "SL_BASE_URL",
        "--",
    )
    user: str = os.getenv("SL_USER", "--")
    password: str = os.getenv("SL_PASSWORD", "--")
    company_db: str = os.getenv("SL_COMPANY_DB", "--")

@dataclass
class Settings:
    db:   DBConfig   = field(default_factory=DBConfig)
    smtp: SMTPConfig = field(default_factory=SMTPConfig)
    sl:   SLConfig   = field(default_factory=SLConfig)

# instância singleton que o resto do código importa
settings = Settings()
