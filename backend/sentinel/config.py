from pathlib import Path

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

    nexar_client_id: str = ""
    nexar_client_secret: str = ""

    siliconexpert_api_key: str = ""
    siliconexpert_api_url: str = "https://api.siliconexpert.com/"
    # When set, GET {api_url}{path} with mpn query param (vendor-specific; set from trial docs)
    siliconexpert_lookup_path: str = ""

    z2data_api_key: str = ""
    z2data_api_url: str = "https://api.z2data.com/"
    z2data_lookup_path: str = ""

    enrichment_cache_days: int = 7
    enrichment_rate_limit_delay: float = 0.5
    risk_default_profile: str = "default"
    # Comma-separated source order (first wins per field when merging for scoring/UI)
    enrichment_source_priority: str = "siliconexpert,z2data,nexar,synthetic"

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
    )

    def enrichment_priority_tuple(self) -> tuple[str, ...]:
        parts = [p.strip().lower() for p in self.enrichment_source_priority.split(",") if p.strip()]
        return tuple(parts) if parts else ("siliconexpert", "z2data", "nexar", "synthetic")


settings = Settings()
