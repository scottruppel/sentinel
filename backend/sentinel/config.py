from pydantic_settings import BaseSettings


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

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def enrichment_priority_tuple(self) -> tuple[str, ...]:
        parts = [p.strip().lower() for p in self.enrichment_source_priority.split(",") if p.strip()]
        return tuple(parts) if parts else ("siliconexpert", "z2data", "nexar", "synthetic")


settings = Settings()
