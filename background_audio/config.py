from __future__ import annotations

from pathlib import Path
from typing import Literal, Tuple, Type

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MAGICTALES_",
        extra="ignore",
    )

    # GCP
    gcp_project: str = ""
    gcp_location: str = "us-central1"

    # Lyria
    lyria_model: Literal["lyria-002", "lyria-3-clip-preview", "lyria-3-pro-preview"] = "lyria-002"
    max_concurrent_generations: int = 3

    # LLM for text analysis
    llm_provider: Literal["claude", "gemini"] = "claude"
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Output
    output_dir: Path = Field(default=Path("output"))
    cache_dir: Path = Field(default=Path(".cache/magictales"))
    cache_enabled: bool = True

    # Chunking
    min_section_words: int = 200
    max_section_words: int = 3000

    # Music defaults
    default_bpm_min: int = 70
    default_bpm_max: int = 140

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        yaml_path = Path("config.yaml")
        if yaml_path.exists():
            return (init_settings, env_settings, YamlConfigSettingsSource(settings_cls, yaml_file=yaml_path))
        return (init_settings, env_settings)


def load_settings(**overrides: object) -> Settings:
    """Load settings with optional CLI overrides."""
    return Settings(**{k: v for k, v in overrides.items() if v is not None})
