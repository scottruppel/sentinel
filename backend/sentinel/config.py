from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolved_env_files() -> tuple[str, ...] | None:
    """Load all present ``.env`` files so nothing is silently ignored.

    Order: **repo root first**, then **backend/** — later files override earlier (local overrides).
    Previously only the first existing file was loaded; if ``backend/.env`` existed, root ``.env`` was never read.
    """
    backend_dir = Path(__file__).resolve().parent.parent
    repo_root = backend_dir.parent
    paths: list[Path] = []
    for candidate in (repo_root / ".env", backend_dir / ".env"):
        if candidate.is_file():
            paths.append(candidate)
    return tuple(str(p) for p in paths) if paths else None


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://sentinel:sentinel@localhost:5432/sentinel"

    nexar_client_id: str = Field(
        default="",
        validation_alias=AliasChoices("nexar_client_id", "NEXAR_CLIENT_ID"),
    )
    nexar_client_secret: str = Field(
        default="",
        validation_alias=AliasChoices("nexar_client_secret", "NEXAR_CLIENT_SECRET"),
    )

    siliconexpert_api_key: str = ""
    siliconexpert_api_url: str = "https://api.siliconexpert.com/"
    # When set, GET {api_url}{path} with mpn query param (vendor-specific; set from trial docs)
    siliconexpert_lookup_path: str = ""

    z2data_api_key: str = ""
    z2data_api_url: str = "https://api.z2data.com/"
    z2data_lookup_path: str = ""

    # Distributor APIs (optional — enrich alongside Nexar)
    mouser_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("mouser_api_key", "MOUSER_API_KEY", "MOUSER_KEY"),
    )
    mouser_api_url: str = "https://api.mouser.com/api/v1"
    digikey_client_id: str = ""
    digikey_client_secret: str = ""
    digikey_use_sandbox: bool = False

    # FRED macro signals (optional — intelligence ingest)
    fred_api_key: str = ""
    # Comma-separated FRED series ids (see fred.stlouisfed.org); used as defaults for ingest
    fred_default_series: str = "INDPRO,PAYEMS,DTWEXBGS"

    enrichment_cache_days: int = 7
    enrichment_rate_limit_delay: float = 0.5
    risk_default_profile: str = "default"
    # Comma-separated source order (first wins per field when merging for scoring/UI)
    enrichment_source_priority: str = "mouser,digikey,nexar,siliconexpert,z2data,synthetic"

    # Agent API access — set a strong random string; required when TAILSCALE_ENABLED=true
    sentinel_api_key: str = ""
    tailscale_enabled: bool = False

    # Intelligence — OpenAI-compatible (Ollama, LM Studio) OR Anthropic Messages API (Claude)
    # Set secrets only via environment / .env (never commit keys to this file).
    llm_enabled: bool = False
    llm_provider: str = "openai"  # "openai" | "anthropic"
    llm_base_url: str = "http://127.0.0.1:11434/v1"
    llm_model: str = "llama3.2"
    llm_api_key: str = ""
    llm_max_tokens: int = 1200
    anthropic_api_version: str = "2023-06-01"

    model_config = SettingsConfigDict(
        env_file=_resolved_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",  # .env may contain other app/API keys not declared on this model
        populate_by_name=True,
    )

    def enrichment_priority_tuple(self) -> tuple[str, ...]:
        parts = [p.strip().lower() for p in self.enrichment_source_priority.split(",") if p.strip()]
        return tuple(parts) if parts else ("mouser", "digikey", "nexar", "siliconexpert", "z2data", "synthetic")

    def fred_series_list(self) -> list[str]:
        return [s.strip() for s in self.fred_default_series.split(",") if s.strip()]


settings = Settings()
