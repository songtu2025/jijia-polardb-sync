from pathlib import Path
from types import SimpleNamespace

import pytest

from backend.app.services import runtime_startup_service
from backend.app.services.migration_preflight_service import PreflightResult

PROJECT_ROOT = Path(__file__).resolve().parents[2]
API_CONFIG_PATH = PROJECT_ROOT / "config" / "api_config.example.yaml"
API_CATALOG_PATH = PROJECT_ROOT / "config" / "jijia_api_catalog.generated.json"


def _settings(app_env: str) -> SimpleNamespace:
    return SimpleNamespace(
        app_env=app_env,
        api_config_path=API_CONFIG_PATH,
        api_catalog_path=API_CATALOG_PATH,
    )


def test_startup_redacts_api_config_error(monkeypatch) -> None:
    secret = "secret-value-at-C:/private/api.yaml"

    def fail_to_load(_engine: object) -> None:
        raise ValueError(secret)

    monkeypatch.setattr(runtime_startup_service, "load_published_api_configs", fail_to_load)

    with pytest.raises(RuntimeError) as error:
        runtime_startup_service.validate_runtime_startup(
            _settings("local"),
            object(),
        )

    assert str(error.value) == "RUNTIME_API_CONFIG_INVALID"
    assert error.value.__suppress_context__ is True
    assert secret not in str(error.value)


def test_local_startup_validates_published_config_without_runtime_target_probe(monkeypatch) -> None:
    verifier_called = False

    def verifier(_engine: object) -> PreflightResult:
        nonlocal verifier_called
        verifier_called = True
        return PreflightResult("pass", "RUNTIME_TARGET_READY")

    monkeypatch.setattr(runtime_startup_service, "verify_runtime_target", verifier)
    monkeypatch.setattr(
        runtime_startup_service,
        "load_published_api_configs",
        lambda _engine: [{"api_code": "example"}],
    )
    monkeypatch.setattr(runtime_startup_service, "load_official_catalog", lambda _path: [])

    runtime_startup_service.validate_runtime_startup(
        _settings("local"),
        object(),
    )

    assert verifier_called is False


def test_production_startup_requires_runtime_target(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_startup_service,
        "verify_runtime_target",
        lambda _engine: PreflightResult("blocked", "RUNTIME_DATABASE_READ_ONLY"),
    )
    monkeypatch.setattr(
        runtime_startup_service,
        "load_published_api_configs",
        lambda _engine: [{"api_code": "example"}],
    )
    monkeypatch.setattr(runtime_startup_service, "load_official_catalog", lambda _path: [])

    with pytest.raises(RuntimeError, match="RUNTIME_TARGET_NOT_READY") as error:
        runtime_startup_service.validate_runtime_startup(
            _settings("production"),
            object(),
        )

    assert "RUNTIME_DATABASE_READ_ONLY" in str(error.value)


def test_production_startup_accepts_verified_runtime_target(monkeypatch) -> None:
    monkeypatch.setattr(
        runtime_startup_service,
        "verify_runtime_target",
        lambda _engine: PreflightResult("pass", "RUNTIME_TARGET_READY"),
    )
    monkeypatch.setattr(
        runtime_startup_service,
        "load_published_api_configs",
        lambda _engine: [{"api_code": "example"}],
    )
    monkeypatch.setattr(runtime_startup_service, "load_official_catalog", lambda _path: [])

    runtime_startup_service.validate_runtime_startup(
        _settings("production"),
        object(),
    )


def test_production_startup_logs_non_unique_index_drift(monkeypatch) -> None:
    warnings: list[tuple[str, tuple[object, ...]]] = []
    monkeypatch.setattr(
        runtime_startup_service,
        "verify_runtime_target",
        lambda _engine: PreflightResult(
            "pass",
            "RUNTIME_TARGET_READY",
            {"unexpectedNonUniqueIndexCount": 1},
        ),
    )
    monkeypatch.setattr(
        runtime_startup_service,
        "load_published_api_configs",
        lambda _engine: [{"api_code": "example"}],
    )
    monkeypatch.setattr(runtime_startup_service, "load_official_catalog", lambda _path: [])
    monkeypatch.setattr(
        runtime_startup_service.logger,
        "warning",
        lambda message, *args: warnings.append((message, args)),
    )

    runtime_startup_service.validate_runtime_startup(
        _settings("production"),
        object(),
    )

    assert warnings == [
        (
            "RUNTIME_SCHEMA_INDEX_DRIFT unexpected_non_unique=%s legacy_non_unique=%s",
            (1, 0),
        )
    ]
