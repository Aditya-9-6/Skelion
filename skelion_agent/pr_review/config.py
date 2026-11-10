# skelion_agent/pr_review/config.py — .skelion.yml Configuration Schema & Loader
"""
Configuration parser and validator for repository-level .skelion.yml.
Strictly validates keys against the schema; unknown keys raise a ValidationError
containing the offending key name.
"""

from typing import List, Optional, Dict, Any
import yaml
from pydantic import BaseModel, Field, model_validator, Extra


class SkelionConfigError(ValueError):
    """Raised when .skelion.yml contains invalid structure or unknown keys."""
    pass


class ReviewConfig(BaseModel):
    lanes: List[str] = Field(
        default_factory=lambda: [
            "quality",
            "security",
            "dependencies",
            "tests",
            "breaking",
            "migrations",
            "performance",
            "logic",
            "runtime",
            "summary",
        ]
    )
    max_inline_comments: int = Field(default=10, ge=0, le=50)
    min_confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    paths_ignore: List[str] = Field(
        default_factory=lambda: ["docs/**", "**/*.md", "**/generated/**"]
    )
    paths_sensitive: List[str] = Field(
        default_factory=lambda: ["auth/**", "payments/**", "migrations/**"]
    )

    class Config:
        extra = Extra.forbid


class FixConfig(BaseModel):
    mode: str = Field(default="suggest")  # suggest | command | fix_pr | auto
    auto_types: List[str] = Field(default_factory=lambda: ["F1"])  # F1, F2 only
    max_files: int = Field(default=3, ge=1, le=10)
    max_changed_lines: int = Field(default=150, ge=1, le=1000)
    excluded_paths: List[str] = Field(
        default_factory=lambda: [
            ".github/workflows/**",
            "Dockerfile",
            "**/*.lock",
            "infra/**",
        ]
    )

    class Config:
        extra = Extra.forbid

    @model_validator(mode="after")
    def validate_fix_mode_and_types(self):
        valid_modes = {"suggest", "command", "fix_pr", "auto"}
        if self.mode not in valid_modes:
            raise SkelionConfigError(f"Invalid fix.mode: '{self.mode}'. Must be one of {valid_modes}")
        for at in self.auto_types:
            if at not in {"F1", "F2"}:
                raise SkelionConfigError(f"Invalid auto_types entry '{at}'. Only F1 and F2 are allowed in auto mode")
        return self


class BudgetConfig(BaseModel):
    max_credits_per_pr: int = Field(default=40, ge=0, le=500)
    allow_max_model: bool = Field(default=False)

    class Config:
        extra = Extra.forbid


class RuntimeConfig(BaseModel):
    source: str = Field(default="proxy")  # proxy | otlp | none
    window_days: int = Field(default=7, ge=1, le=90)

    class Config:
        extra = Extra.forbid

    @model_validator(mode="after")
    def validate_runtime_source(self):
        valid_sources = {"proxy", "otlp", "none"}
        if self.source not in valid_sources:
            raise SkelionConfigError(f"Invalid runtime.source: '{self.source}'. Must be one of {valid_sources}")
        return self


class ChecksConfig(BaseModel):
    required: bool = Field(default=False)

    class Config:
        extra = Extra.forbid


class SkelionRepoConfig(BaseModel):
    version: int = Field(default=1)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    fix: FixConfig = Field(default_factory=FixConfig)
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    runtime: RuntimeConfig = Field(default_factory=RuntimeConfig)
    checks: ChecksConfig = Field(default_factory=ChecksConfig)

    class Config:
        extra = Extra.forbid

    @model_validator(mode="after")
    def validate_version(self):
        if self.version != 1:
            raise SkelionConfigError(f"Unsupported .skelion.yml version: {self.version}. Only version 1 is supported.")
        return self


def load_skelion_yaml(raw_yaml_or_dict: Any) -> SkelionRepoConfig:
    """
    Parse and strictly validate a repository's .skelion.yml.
    Raises SkelionConfigError if unknown keys exist or values are invalid.
    """
    if raw_yaml_or_dict is None:
        return SkelionRepoConfig()

    data: Dict[str, Any]
    if isinstance(raw_yaml_or_dict, str):
        if not raw_yaml_or_dict.strip():
            return SkelionRepoConfig()
        try:
            parsed = yaml.safe_load(raw_yaml_or_dict)
            data = parsed if isinstance(parsed, dict) else {}
        except Exception as exc:
            raise SkelionConfigError(f"Malformed YAML in .skelion.yml: {exc}") from exc
    elif isinstance(raw_yaml_or_dict, dict):
        data = raw_yaml_or_dict
    else:
        raise SkelionConfigError(f"Expected YAML string or dictionary, got {type(raw_yaml_or_dict).__name__}")

    # Check for unknown keys at top level first to produce clear error message
    known_top_level = {"version", "review", "fix", "budget", "runtime", "checks"}
    unknown_keys = [k for k in data.keys() if k not in known_top_level]
    if unknown_keys:
        raise SkelionConfigError(
            f"Unknown key in .skelion.yml: '{unknown_keys[0]}'. Allowed top-level keys: {sorted(list(known_top_level))}"
        )

    # Check unknown keys in sub-sections
    section_map = {
        "review": {"lanes", "max_inline_comments", "min_confidence", "paths_ignore", "paths_sensitive"},
        "fix": {"mode", "auto_types", "max_files", "max_changed_lines", "excluded_paths"},
        "budget": {"max_credits_per_pr", "allow_max_model"},
        "runtime": {"source", "window_days"},
        "checks": {"required"},
    }
    for sec_name, allowed_keys in section_map.items():
        sub = data.get(sec_name)
        if isinstance(sub, dict):
            sub_unknown = [k for k in sub.keys() if k not in allowed_keys]
            if sub_unknown:
                raise SkelionConfigError(
                    f"Unknown key in .skelion.yml under '{sec_name}': '{sub_unknown[0]}'. Allowed: {sorted(list(allowed_keys))}"
                )

    try:
        return SkelionRepoConfig(**data)
    except Exception as exc:
        raise SkelionConfigError(f"Configuration error in .skelion.yml: {exc}") from exc
