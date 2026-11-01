from skelion_agent.config import Settings, validate_secrets


def test_settings_defaults():
    settings = Settings()
    assert settings.PROJECT_NAME == "Skelion Unified Autonomous Platform"
    assert settings.ENVIRONMENT in ("development", "test")
    assert settings.DATABASE_URL is not None
    assert settings.REDIS_URL is not None


def test_validate_secrets_dev():
    # In development mode, validation should succeed with dev defaults
    missing = validate_secrets(
        raise_on_error=False, exit_on_failure=False, strict=False
    )
    assert isinstance(missing, list)


def test_validate_secrets_strict_missing():
    # In strict mode with empty/dev secrets, should return missing required secrets
    missing = validate_secrets(raise_on_error=False, exit_on_failure=False, strict=True)
    assert len(missing) > 0
    assert any(k in missing for k in ["SECRET_KEY", "ENCRYPTION_KEY"])
