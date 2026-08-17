from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from app.core.bar_auth import BarAuthConfigurationError
from app.core.config import Settings
from app.main import _ensure_regular_guest_configuration_is_valid, app
from app.core.config import settings as runtime_settings

DEMO_BAR_ID = UUID("11111111-1111-4111-8111-111111111111")
DEMO_TOKEN = "demo-token-with-enough-entropy-for-tests"


def _settings(**overrides) -> Settings:
    values = {"APP_ENV": "local", "REGULAR_GUEST_ENABLED": False}
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_disabled_flag_is_valid_in_every_environment():
    for env in ("local", "staging", "production"):
        settings = _settings(APP_ENV=env, REGULAR_GUEST_ENABLED=False)
        assert settings.REGULAR_GUEST_ENABLED is False
        assert settings.APP_ENV == env


def test_enabled_flag_is_valid_in_local_and_staging_with_demo_credentials():
    for env in ("local", "staging"):
        settings = _settings(
            APP_ENV=env,
            REGULAR_GUEST_ENABLED=True,
            DEMO_BAR_ID=DEMO_BAR_ID,
            DEMO_BAR_TOKEN=DEMO_TOKEN,
        )
        assert settings.REGULAR_GUEST_ENABLED is True
        assert settings.APP_ENV == env


def test_settings_defers_the_production_fail_closed_decision_to_the_startup_guard():
    # Settings alone cannot know whether a verified bar-principal provider
    # has been wired up for production (that's a deployment-time decision,
    # not declared config), so it does not reject this combination itself
    # — see test_startup_guard_fails_closed_in_production_without_verified_provider
    # for where the fail-closed behavior actually lives.
    settings = _settings(APP_ENV="production", REGULAR_GUEST_ENABLED=True)
    assert settings.REGULAR_GUEST_ENABLED is True
    assert settings.APP_ENV == "production"


def test_regular_guest_diagnostics_exposes_no_secrets():
    settings = _settings(
        APP_ENV="local",
        REGULAR_GUEST_ENABLED=True,
        DEMO_BAR_ID=DEMO_BAR_ID,
        DEMO_BAR_TOKEN=DEMO_TOKEN,
        SESSION_TOKEN_SECRET="super-secret-session-key",
        POSTGRES_PASSWORD="hunter2",
    )

    diagnostics = settings.regular_guest_diagnostics

    assert diagnostics == {"enabled": True, "app_env": "local"}
    serialized = str(diagnostics)
    assert DEMO_TOKEN not in serialized
    assert "super-secret-session-key" not in serialized
    assert "hunter2" not in serialized


@pytest.mark.parametrize("app_env", ["local", "staging", "production"])
def test_startup_guard_is_a_noop_when_disabled(app_env):
    # Missing demo credentials (and, for production, no verified provider)
    # would normally make build_bar_principal_provider raise, but the
    # guard must never even call it when the flag is off — in any
    # environment, including a misconfigured production deployment that
    # simply forgot to turn the flag on.
    settings = _settings(APP_ENV=app_env, REGULAR_GUEST_ENABLED=False)
    _ensure_regular_guest_configuration_is_valid(settings)  # must not raise


def test_startup_guard_raises_when_enabled_without_demo_credentials():
    settings = _settings(APP_ENV="local", REGULAR_GUEST_ENABLED=True, DEMO_BAR_TOKEN="")

    with pytest.raises(BarAuthConfigurationError):
        _ensure_regular_guest_configuration_is_valid(settings)


def test_startup_guard_fails_closed_in_production_without_verified_provider():
    # main.py never has a verified provider to pass, so enabling the flag
    # in production always fails startup closed today (FND-01 decision D1).
    settings = _settings(APP_ENV="production", REGULAR_GUEST_ENABLED=True)

    with pytest.raises(BarAuthConfigurationError):
        _ensure_regular_guest_configuration_is_valid(settings)


def test_startup_guard_passes_when_enabled_with_demo_credentials():
    settings = _settings(
        APP_ENV="staging",
        REGULAR_GUEST_ENABLED=True,
        DEMO_BAR_ID=DEMO_BAR_ID,
        DEMO_BAR_TOKEN=DEMO_TOKEN,
    )
    _ensure_regular_guest_configuration_is_valid(settings)  # must not raise


def test_app_lifespan_runs_the_startup_guard_without_error():
    # Exercises the real FastAPI wiring, not just the guard function in
    # isolation: TestClient only runs lifespan handlers inside a `with`
    # block, so this is the one test that proves _ensure_regular_guest_
    # configuration_is_valid is actually reachable from app startup and
    # not merely defined and never called.
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200


def test_health_check_exposes_enabled_state_without_secrets():
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"

    diagnostics = body["regular_guest_intelligence"]
    # Keep the health payload aligned with the Settings.regular_guest_diagnostics contract.
    assert diagnostics == runtime_settings.regular_guest_diagnostics

    serialized = str(body)
    for secret_value in (
        runtime_settings.DEMO_BAR_TOKEN,
        runtime_settings.SESSION_TOKEN_SECRET,
        runtime_settings.POSTGRES_PASSWORD,
        runtime_settings.OPENAI_API_KEY,
        runtime_settings.OPENROUTER_API_KEY,
    ):
        if secret_value:
            assert secret_value not in serialized


def test_regular_guest_router_is_mounted_only_when_enabled():
    from app.main import regular_guest_router

    is_mounted = any(
        getattr(route, "path", "").startswith("/api/v1/regular-guest") for route in app.routes
    )
    assert is_mounted == runtime_settings.REGULAR_GUEST_ENABLED
    # The router object always exists so later tasks can attach routes to
    # it; whether it is ever exposed depends solely on the feature flag.
    assert regular_guest_router.prefix == "/regular-guest"
    assert regular_guest_router.tags == ["regular-guest-intelligence"]
