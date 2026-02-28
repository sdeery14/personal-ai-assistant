"""Prompt registry service — load, seed, and version prompts via MLflow."""

from dataclasses import dataclass
from typing import Optional

import mlflow
import structlog

from src.config import get_settings
from src.prompts.defaults import PROMPT_DEFAULTS

logger = structlog.get_logger(__name__)

settings = get_settings()

# Module-level dict tracking currently loaded prompt versions
_active_versions: dict[str, int] = {}


@dataclass
class PromptVersionInfo:
    """Full metadata for a loaded prompt version."""

    name: str
    version: int
    alias: str
    template: str
    model_config: Optional[dict] = None
    is_fallback: bool = False


def _default_model_config() -> dict:
    """Build the default model_config dict from application settings."""
    return {
        "model": settings.openai_model,
        "max_tokens": settings.max_tokens,
    }


def seed_prompts() -> dict[str, int]:
    """Seed missing prompts into the MLflow registry from bundled defaults.

    Returns:
        Dict mapping prompt name to version number for each newly seeded prompt.
        Empty dict if all prompts already exist or on connection failure.
    """
    seeded: dict[str, int] = {}
    skipped = 0
    default_config = _default_model_config()

    try:
        for name, template in PROMPT_DEFAULTS.items():
            existing = mlflow.genai.load_prompt(name, allow_missing=True)
            if existing is not None:
                skipped += 1
                continue
            version = mlflow.genai.register_prompt(
                name=name,
                template=template,
                model_config=default_config,
            )
            mlflow.genai.set_prompt_alias(
                name=name,
                alias="production",
                version=version.version,
            )
            seeded[name] = version.version
    except Exception:
        logger.warning("prompt_seeding_failed", error_type="connection")
        return {}

    logger.info("prompt_seeding_complete", seeded=len(seeded), skipped=skipped)
    return seeded


def register_prompt(
    name: str,
    template: str,
    commit_message: str | None = None,
    model_config: dict | None = None,
) -> int:
    """Register a new version of a prompt in the registry.

    Returns:
        New version number.
    """
    version = mlflow.genai.register_prompt(
        name=name,
        template=template,
        commit_message=commit_message,
        model_config=model_config,
    )
    return version.version


def get_active_prompt_versions() -> dict[str, int]:
    """Return a copy of all currently loaded prompt names and their version numbers."""
    return dict(_active_versions)


def load_prompt(name: str, alias: str | None = None) -> str:
    """Load a prompt's text from the registry, with fallback to bundled defaults.

    Args:
        name: Registry prompt name (e.g., "orchestrator-base").
        alias: Optional alias override. Defaults to configured PROMPT_ALIAS.

    Returns:
        Prompt text string. Never returns None — always falls back to bundled default.
    """
    resolved_alias = alias or settings.prompt_alias
    uri = f"prompts:/{name}@{resolved_alias}"

    try:
        prompt_version = mlflow.genai.load_prompt(
            uri,
            cache_ttl_seconds=settings.prompt_cache_ttl_seconds,
        )
        _active_versions[name] = prompt_version.version
        logger.info(
            "prompt_loaded",
            prompt_name=name,
            version=prompt_version.version,
            alias=resolved_alias,
            is_fallback=False,
        )
        return prompt_version.template
    except Exception:
        logger.warning(
            "prompt_load_fallback",
            prompt_name=name,
            alias=resolved_alias,
            is_fallback=True,
        )
        _active_versions[name] = 0
        return PROMPT_DEFAULTS[name]


def load_prompt_version(name: str, alias: str | None = None) -> PromptVersionInfo:
    """Load a prompt with full version metadata.

    Args:
        name: Registry prompt name.
        alias: Optional alias override.

    Returns:
        PromptVersionInfo with full metadata. is_fallback=True if loaded from bundled defaults.
    """
    resolved_alias = alias or settings.prompt_alias
    uri = f"prompts:/{name}@{resolved_alias}"

    try:
        pv = mlflow.genai.load_prompt(
            uri,
            cache_ttl_seconds=settings.prompt_cache_ttl_seconds,
        )
        _active_versions[name] = pv.version
        logger.info(
            "prompt_loaded",
            prompt_name=name,
            version=pv.version,
            alias=resolved_alias,
            is_fallback=False,
        )
        return PromptVersionInfo(
            name=name,
            version=pv.version,
            alias=resolved_alias,
            template=pv.template,
            model_config=pv.model_config,
            is_fallback=False,
        )
    except Exception:
        logger.warning(
            "prompt_load_fallback",
            prompt_name=name,
            alias=resolved_alias,
            is_fallback=True,
        )
        _active_versions[name] = 0
        return PromptVersionInfo(
            name=name,
            version=0,
            alias=resolved_alias,
            template=PROMPT_DEFAULTS[name],
            model_config=None,
            is_fallback=True,
        )


def set_alias(name: str, alias: str, version: int) -> None:
    """Point an alias to a specific prompt version.

    Args:
        name: Registry prompt name.
        alias: Alias name (e.g., "production", "experiment").
        version: Version number to point to.
    """
    mlflow.genai.set_prompt_alias(name=name, alias=alias, version=version)
    logger.info("prompt_alias_updated", prompt_name=name, alias=alias, version=version)
