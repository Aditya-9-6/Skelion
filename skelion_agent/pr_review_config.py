# skelion_agent/pr_review_config.py
"""
Configuration schema definition and validator for .skelion.yml.
Strictly forbids unknown keys with clear descriptive error messages.
"""

from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
import yaml


class SeverityLevel(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FixMode(str, Enum):
    SUGGEST = "suggest"
    BRANCH = "branch"
    PR = "pr"
    COMMIT = "commit"
    OFF = "off"


class LaneConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    rules: Optional[List[str]] = None
    exclude_rules: Optional[List[str]] = None
    config_file: Optional[str] = None
    extra_args: Optional[List[str]] = None
    timeout_sec: Optional[int] = None
    severity_threshold: Optional[SeverityLevel] = None
    model: Optional[str] = None
    temperature: Optional[float] = None


class FixConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    mode: FixMode = FixMode.SUGGEST
    max_fixes: int = Field(default=5, ge=0)
    verification: bool = True
    target_branch_prefix: Optional[str] = "skelion-fix/"
    auto_commit: bool = False


class RulesConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ignore: List[str] = Field(default_factory=list)
    exclude: List[str] = Field(default_factory=list)
    severity_threshold: SeverityLevel = SeverityLevel.MEDIUM
    confidence_threshold: ConfidenceLevel = ConfidenceLevel.MEDIUM
    fail_on_severity: Optional[SeverityLevel] = None


class SuppressionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rule_id: Optional[str] = None
    path: Optional[str] = None
    path_pattern: Optional[str] = None
    reason: Optional[str] = None
    owner: Optional[str] = None
    expires_at: Optional[str] = None


class ReviewConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    comment_on_pr: bool = True
    summary_table: bool = True
    inline_comments: bool = True
    fail_check_run_on_findings: bool = False
    max_comments: int = 25


class LimitsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_files: int = 500
    max_diff_lines: int = 5000
    credit_budget_milli: Optional[int] = None
    timeout_sec: int = 300


class SkelionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    lanes: Dict[str, LaneConfig] = Field(default_factory=dict)
    fix: FixConfig = Field(default_factory=FixConfig)
    rules: RulesConfig = Field(default_factory=RulesConfig)
    suppressions: List[SuppressionItem] = Field(default_factory=list)
    review: ReviewConfig = Field(default_factory=ReviewConfig)
    limits: LimitsConfig = Field(default_factory=LimitsConfig)
    plan_tier: Optional[str] = None

    @field_validator("lanes", mode="before")
    @classmethod
    def normalize_lanes(cls, v: Any) -> Dict[str, Any]:
        if isinstance(v, list):
            res = {}
            for item in v:
                if isinstance(item, str):
                    res[item] = {"enabled": True}
                elif isinstance(item, dict):
                    res.update(item)
            return res
        return v or {}


class ConfigValidationError(ValueError):
    """Raised when .skelion.yml configuration fails validation or contains unknown keys."""

    def __init__(self, message: str, details: Optional[List[Dict[str, Any]]] = None):
        super().__init__(message)
        self.details = details or []


def compute_config_sha(content: Union[str, bytes, Dict[str, Any]]) -> str:
    """Compute SHA-256 hash of configuration content."""
    if isinstance(content, dict):
        raw = json.dumps(content, sort_keys=True).encode("utf-8")
    elif isinstance(content, str):
        raw = content.encode("utf-8")
    else:
        raw = bytes(content)
    return hashlib.sha256(raw).hexdigest()


def validate_config(raw: Union[str, bytes, Dict[str, Any]]) -> SkelionConfig:
    """
    Validate .skelion.yml configuration from raw YAML string/bytes or a parsed dictionary.
    Unknown keys fail validation with a clear ConfigValidationError.
    """
    if isinstance(raw, (str, bytes)):
        text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
        if not text.strip():
            return SkelionConfig()
        try:
            parsed = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise ConfigValidationError(f"Invalid YAML syntax in .skelion.yml: {exc}") from exc
        if parsed is None:
            return SkelionConfig()
        if not isinstance(parsed, dict):
            raise ConfigValidationError("Configuration in .skelion.yml must be a mapping/dictionary")
    elif isinstance(raw, dict):
        parsed = raw
    else:
        raise ConfigValidationError("Input must be a YAML string, bytes, or dictionary")

    try:
        return SkelionConfig.model_validate(parsed)
    except ValidationError as exc:
        error_messages = []
        for err in exc.errors():
            loc_parts = [str(p) for p in err.get("loc", ())]
            loc_str = " -> ".join(loc_parts) if loc_parts else "root"
            err_type = err.get("type", "")
            if err_type == "extra_forbidden":
                extra_key = loc_parts[-1] if loc_parts else "unknown"
                parent = " -> ".join(loc_parts[:-1]) if len(loc_parts) > 1 else "top-level"
                error_messages.append(
                    f"Unknown key '{extra_key}' in {parent} configuration is not allowed in .skelion.yml"
                )
            else:
                msg = err.get("msg", "Invalid value")
                error_messages.append(f"Validation error at '{loc_str}': {msg}")

        full_message = "; ".join(error_messages)
        raise ConfigValidationError(full_message, details=exc.errors()) from exc


def load_config_from_file(file_path: Union[str, Path]) -> SkelionConfig:
    """Load and validate .skelion.yml configuration from a file path."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    content = path.read_text(encoding="utf-8")
    return validate_config(content)
