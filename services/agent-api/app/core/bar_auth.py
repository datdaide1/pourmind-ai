"""Trusted bar-principal resolution for bar-scoped APIs.

Conversation session credentials and bar credentials are deliberately checked
independently. A client supplied bar ID is a resource locator, never proof that
the caller belongs to that bar.
"""

from __future__ import annotations

import hmac
import logging
from dataclasses import dataclass
from typing import Annotated, Protocol
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, settings
from app.core.session_auth import require_session_token


logger = logging.getLogger(__name__)


class BarAuthConfigurationError(RuntimeError):
    """Raised when bar-scoped routes cannot be enabled safely."""


@dataclass(frozen=True, slots=True)
class BarPrincipal:
    bar_id: UUID
    subject: str
    provider: str
    verified: bool


class BarPrincipalProvider(Protocol):
    def resolve(
        self,
        *,
        bar_id: UUID | None,
        bar_token: str | None,
        session_id: str | None,
        session_token: str | None,
    ) -> BarPrincipal: ...


class VerifiedBarPrincipalProvider(BarPrincipalProvider, Protocol):
    """Provider explicitly approved to establish production bar identity."""

    is_verified_provider: bool


@dataclass(frozen=True, slots=True)
class ProductionBarPrincipalProvider:
    """Fail-closed adapter that enforces verified production principals."""

    provider: VerifiedBarPrincipalProvider

    def resolve(
        self,
        *,
        bar_id: UUID | None,
        bar_token: str | None,
        session_id: str | None,
        session_token: str | None,
    ) -> BarPrincipal:
        principal = self.provider.resolve(
            bar_id=bar_id,
            bar_token=bar_token,
            session_id=session_id,
            session_token=session_token,
        )
        if not principal.verified:
            logger.error(
                "bar_auth_denied reason=unverified_production_principal bar_id=%s",
                principal.bar_id,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Verified bar principal unavailable",
            )
        return principal


@dataclass(frozen=True, slots=True)
class DemoBarPrincipalProvider:
    """Single-bar provider for disposable local and staging data only."""

    demo_bar_id: UUID
    demo_bar_token: str

    def resolve(
        self,
        *,
        bar_id: UUID | None,
        bar_token: str | None,
        session_id: str | None,
        session_token: str | None,
    ) -> BarPrincipal:
        if not session_id or not session_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing session credentials")
        require_session_token(session_id, session_token)

        if bar_id is None or not bar_token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bar credentials")
        if not hmac.compare_digest(self.demo_bar_token, bar_token):
            logger.warning("bar_auth_denied reason=invalid_bar_credentials bar_id=%s", bar_id)
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid bar credentials")
        if bar_id != self.demo_bar_id:
            # Do not reveal whether a resource exists in another tenant.
            logger.warning("bar_auth_denied reason=bar_mismatch bar_id=%s", bar_id)
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bar resource not found")

        logger.info("bar_auth_resolved provider=demo bar_id=%s", self.demo_bar_id)
        return BarPrincipal(
            bar_id=self.demo_bar_id,
            subject=f"demo-session:{session_id}",
            provider="demo",
            verified=False,
        )


def build_bar_principal_provider(
    runtime_settings: Settings,
    *,
    verified_provider: VerifiedBarPrincipalProvider | None = None,
) -> BarPrincipalProvider:
    """Build a provider or fail before protected routes are registered."""

    if runtime_settings.APP_ENV == "production":
        if (
            verified_provider is None
            or getattr(verified_provider, "is_verified_provider", False) is not True
        ):
            raise BarAuthConfigurationError(
                "Production bar-scoped routes require a verified principal provider"
            )
        return ProductionBarPrincipalProvider(verified_provider)

    if runtime_settings.APP_ENV not in {"local", "staging"}:
        raise BarAuthConfigurationError("Unsupported runtime environment")
    if runtime_settings.DEMO_BAR_ID is None or not runtime_settings.DEMO_BAR_TOKEN:
        raise BarAuthConfigurationError(
            "Local/staging bar-scoped routes require DEMO_BAR_ID and DEMO_BAR_TOKEN"
        )
    return DemoBarPrincipalProvider(
        demo_bar_id=runtime_settings.DEMO_BAR_ID,
        demo_bar_token=runtime_settings.DEMO_BAR_TOKEN,
    )


def principal_dependency(provider: BarPrincipalProvider):
    """Create the FastAPI dependency used by future bar-scoped routers."""

    def resolve_principal(
        x_bar_id: Annotated[UUID | None, Header(alias="X-Bar-ID")] = None,
        x_bar_token: Annotated[str | None, Header(alias="X-Bar-Token")] = None,
        x_session_id: Annotated[str | None, Header(alias="X-Session-ID")] = None,
        x_session_token: Annotated[str | None, Header(alias="X-Session-Token")] = None,
    ) -> BarPrincipal:
        return provider.resolve(
            bar_id=x_bar_id,
            bar_token=x_bar_token,
            session_id=x_session_id,
            session_token=x_session_token,
        )

    return resolve_principal


def require_resource_bar(principal: BarPrincipal, resource_bar_id: UUID) -> None:
    """Apply the non-enumerating cross-bar resource policy."""

    if principal.bar_id != resource_bar_id:
        logger.warning(
            "bar_resource_denied principal_bar_id=%s resource_bar_id=%s",
            principal.bar_id,
            resource_bar_id,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bar resource not found")


def configured_bar_principal_dependency():
    """Opt-in dependency for routers registered by FND-06.

    Construction is deferred so importing the current application does not
    enable unfinished routes or require demo credentials.
    """

    provider = build_bar_principal_provider(settings)
    return Depends(principal_dependency(provider))
