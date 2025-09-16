"""Configuration du scraper avec Pydantic Settings (Pydantic v2)."""

import os
from typing import List, Optional

from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration du scraper Amazon."""

    # Proxies
    proxy_pool: Optional[List[str]] = Field(None, env="PROXY_POOL")
    
    # Navigateur
    headless: bool = Field(True, env="HEADLESS")
    timeout_ms: int = Field(45000, env="TIMEOUT_MS")
    max_contexts: int = Field(2, env="MAX_CONTEXTS")
    
    # Scraping
    max_pages_per_asin: int = Field(5, env="MAX_PAGES_PER_ASIN")
    sleep_min: float = Field(2.0, env="SLEEP_MIN")
    sleep_max: float = Field(4.0, env="SLEEP_MAX")
    language: str = Field("fr_FR", env="LANGUAGE")
    sort: str = Field("recent", env="SORT")
    
    # Base de données
    db_url: str = Field("sqlite:///./reviews.db", env="DB_URL")
    
    # Auth Amazon (optionnel)
    storage_state_path: str = Field("./storage_state.json", env="STORAGE_STATE_PATH")
    amz_email: Optional[str] = Field(None, env="AMZ_EMAIL")
    amz_password: Optional[str] = Field(None, env="AMZ_PASSWORD")

    # Profil persistant (Option A)
    use_persistent_profile: bool = Field(True, env="USE_PERSISTENT_PROFILE")
    user_data_dir: str = Field("./pw_profile", env="USER_DATA_DIR")
    
    # User agents pool
    user_agents: List[str] = Field(
        default_factory=lambda: [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        ]
    )
    
    @validator("proxy_pool")
    def parse_proxy_pool(cls, v: Optional[str]) -> Optional[List[str]]:
        """Parse la liste de proxies depuis une chaîne séparée par des virgules."""
        if not v:
            return None
        return [proxy.strip() for proxy in v.split(",") if proxy.strip()]
    
    @validator("sleep_max")
    def validate_sleep_range(cls, v: float, values: dict) -> float:
        """Valide que sleep_max >= sleep_min."""
        if "sleep_min" in values and v < values["sleep_min"]:
            raise ValueError("sleep_max doit être >= sleep_min")
        return v
    
    @validator("max_contexts")
    def validate_max_contexts(cls, v: int) -> int:
        """Valide que max_contexts est positif."""
        if v <= 0:
            raise ValueError("max_contexts doit être > 0")
        return v
    
    @validator("max_pages_per_asin")
    def validate_max_pages(cls, v: int) -> int:
        """Valide que max_pages_per_asin est positif."""
        if v <= 0:
            raise ValueError("max_pages_per_asin doit être > 0")
        return v

    # Configuration Pydantic v2
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


# Instance globale des settings
settings = Settings()
