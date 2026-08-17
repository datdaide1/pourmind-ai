from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.bar_auth import (
    BarAuthConfigurationError,
    BarPrincipal,
    DemoBarPrincipalProvider,
    ProductionBarPrincipalProvider,
    build_bar_principal_provider,
    principal_dependency,
    require_resource_bar,
)
from app.core.config import Settings
from app.core.session_auth import create_session_token


BAR_A = UUID("11111111-1111-4111-8111-111111111111")
BAR_B = UUID("22222222-2222-4222-8222-222222222222")
DEMO_TOKEN = "demo-token-with-enough-entropy-for-tests"
SESSION_ID = "session-a"


def make_settings(**overrides) -> Settings:
    values = {
        "APP_ENV": "local",
        "REGULAR_GUEST_ENABLED": True,
        "DEMO_BAR_ID": BAR_A,
        "DEMO_BAR_TOKEN": DEMO_TOKEN,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def auth_headers(*, bar_id: UUID = BAR_A, bar_token: str = DEMO_TOKEN) -> dict[str, str]:
    return {
        "X-Bar-ID": str(bar_id),
        "X-Bar-Token": bar_token,
        "X-Session-ID": SESSION_ID,
        "X-Session-Token": create_session_token(SESSION_ID),
    }


def test_local_provider_resolves_configured_demo_bar_and_session() -> None:
    provider = build_bar_principal_provider(make_settings())
    principal = provider.resolve(
        bar_id=BAR_A,
        bar_token=DEMO_TOKEN,
        session_id=SESSION_ID,
        session_token=create_session_token(SESSION_ID),
    )

    assert principal == BarPrincipal(
        bar_id=BAR_A,
        subject=f"demo-session:{SESSION_ID}",
        provider="demo",
        verified=False,
    )


@pytest.mark.parametrize(
    ("kwargs", "status_code"),
    [
        ({"bar_id": None, "bar_token": None}, 401),
        ({"bar_id": BAR_A, "bar_token": "wrong"}, 403),
        ({"bar_id": BAR_B, "bar_token": DEMO_TOKEN}, 404),
    ],
)
def test_demo_provider_rejects_missing_invalid_and_mismatched_bar(kwargs, status_code) -> None:
    provider = DemoBarPrincipalProvider(BAR_A, DEMO_TOKEN)
    with pytest.raises(HTTPException) as exc_info:
        provider.resolve(
            session_id=SESSION_ID,
            session_token=create_session_token(SESSION_ID),
            **kwargs,
        )
    assert exc_info.value.status_code == status_code


def test_session_token_alone_does_not_grant_bar_access() -> None:
    provider = DemoBarPrincipalProvider(BAR_A, DEMO_TOKEN)
    with pytest.raises(HTTPException) as exc_info:
        provider.resolve(
            bar_id=BAR_A,
            bar_token=None,
            session_id=SESSION_ID,
            session_token=create_session_token(SESSION_ID),
        )
    assert exc_info.value.status_code == 401


def test_production_fails_closed_without_verified_provider() -> None:
    with pytest.raises(BarAuthConfigurationError, match="verified principal provider"):
        build_bar_principal_provider(make_settings(APP_ENV="production"))


def test_production_accepts_only_explicit_verified_provider() -> None:
    class VerifiedProvider:
        is_verified_provider = True

        def resolve(self, **kwargs):
            return BarPrincipal(BAR_A, "verified-user", "oidc", True)

    verified = VerifiedProvider()
    provider = build_bar_principal_provider(
        make_settings(APP_ENV="production"), verified_provider=verified
    )
    assert isinstance(provider, ProductionBarPrincipalProvider)
    assert provider.resolve(
        bar_id=BAR_A,
        bar_token=None,
        session_id=None,
        session_token=None,
    ).verified is True


def test_production_rejects_demo_provider_even_when_explicitly_supplied() -> None:
    with pytest.raises(BarAuthConfigurationError, match="verified principal provider"):
        build_bar_principal_provider(
            make_settings(APP_ENV="production"),
            verified_provider=DemoBarPrincipalProvider(BAR_A, DEMO_TOKEN),
        )


def test_production_rejects_unverified_principal_from_trusted_provider() -> None:
    class BrokenVerifiedProvider:
        is_verified_provider = True

        def resolve(self, **kwargs):
            return BarPrincipal(BAR_A, "unverified-user", "broken-oidc", False)

    provider = build_bar_principal_provider(
        make_settings(APP_ENV="production"),
        verified_provider=BrokenVerifiedProvider(),
    )
    with pytest.raises(HTTPException) as exc_info:
        provider.resolve(
            bar_id=BAR_A,
            bar_token=None,
            session_id=None,
            session_token=None,
        )
    assert exc_info.value.status_code == 503


def test_default_environment_fails_closed_to_production() -> None:
    assert Settings(_env_file=None).APP_ENV == "production"


def test_local_fails_closed_when_demo_configuration_is_incomplete() -> None:
    with pytest.raises(BarAuthConfigurationError, match="DEMO_BAR_ID"):
        build_bar_principal_provider(make_settings(DEMO_BAR_ID=None))


def test_endpoint_policy_returns_401_403_and_404_without_leaking_cross_bar_data() -> None:
    app = FastAPI()
    provider = DemoBarPrincipalProvider(BAR_A, DEMO_TOKEN)

    @app.get("/bars/{resource_bar_id}/resource")
    def read_resource(
        resource_bar_id: UUID,
        principal: BarPrincipal = Depends(principal_dependency(provider)),
    ):
        require_resource_bar(principal, resource_bar_id)
        return {"bar_id": str(principal.bar_id)}

    client = TestClient(app)
    assert client.get(f"/bars/{BAR_A}/resource").status_code == 401
    assert client.get(
        f"/bars/{BAR_A}/resource", headers=auth_headers(bar_token="wrong")
    ).status_code == 403
    assert client.get(
        f"/bars/{BAR_B}/resource", headers=auth_headers()
    ).status_code == 404
    assert client.get(
        f"/bars/{BAR_A}/resource", headers=auth_headers(bar_id=BAR_B)
    ).status_code == 404
    assert client.get(
        f"/bars/{BAR_A}/resource", headers=auth_headers()
    ).json() == {"bar_id": str(BAR_A)}


def test_auth_logs_only_operational_identifiers(caplog) -> None:
    provider = DemoBarPrincipalProvider(BAR_A, DEMO_TOKEN)
    with caplog.at_level("INFO", logger="app.core.bar_auth"):
        provider.resolve(
            bar_id=BAR_A,
            bar_token=DEMO_TOKEN,
            session_id=SESSION_ID,
            session_token=create_session_token(SESSION_ID),
        )

    message = caplog.text
    assert str(BAR_A) in message
    assert DEMO_TOKEN not in message
    assert create_session_token(SESSION_ID) not in message
    assert "notes" not in message.lower()
    assert "allerg" not in message.lower()
