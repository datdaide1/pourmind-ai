from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api import router as api_router
from app.core.bar_auth import build_bar_principal_provider
from app.core.middleware import ApiProtectionMiddleware, BraintrustTracingMiddleware
from app.core.config import Settings, settings
from app.domain.openapi import install_domain_openapi

app = FastAPI(
    title="PourMind AI Agent API",
    description="Agentic AI API for B2C mixology and B2B bar intelligence",
    version="1.0.0",
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Session-Token"],
)

app.add_middleware(BraintrustTracingMiddleware)

app.include_router(api_router, prefix="/api/v1")
app.add_middleware(ApiProtectionMiddleware)
install_domain_openapi(app)


def _ensure_regular_guest_configuration_is_valid(runtime_settings: Settings) -> None:
    """FND-06: fail fast at process startup, not at first request, when
    Regular Guest Intelligence is enabled with a configuration that would
    break at runtime. build_bar_principal_provider() already fails closed
    in production (no verified provider is wired up here) and in
    local/staging without demo bar credentials configured — both surface
    as BarAuthConfigurationError instead of a working-until-first-request
    deployment (FND-01 decision D1)."""
    if not runtime_settings.REGULAR_GUEST_ENABLED:
        return
    build_bar_principal_provider(runtime_settings)


_ensure_regular_guest_configuration_is_valid(settings)

# Regular Guest Intelligence routes attach themselves to this router in
# later tasks (RCP-03, MNU-02, PTR-01/04, INT-07). It is only mounted when
# the feature flag is on, so a disabled deployment has no trace of these
# routes in its live OpenAPI schema at all, not merely a 404 per request.
regular_guest_router = APIRouter(prefix="/regular-guest", tags=["regular-guest-intelligence"])
if settings.REGULAR_GUEST_ENABLED:
    app.include_router(regular_guest_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "regular_guest_intelligence": settings.regular_guest_diagnostics,
    }
