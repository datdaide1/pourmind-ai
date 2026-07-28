from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api import router as api_router
from app.core.middleware import BraintrustTracingMiddleware

app = FastAPI(
    title="PourMind AI Agent API",
    description="Agentic AI API for B2C mixology and B2B bar intelligence",
    version="1.0.0",
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = exc.errors()
    is_missing = all(err.get("type") == "missing" or "missing" in err.get("type", "") for err in errors)
    if is_missing:
        return JSONResponse(
            status_code=422,
            content={"detail": errors}
        )
    else:
        return JSONResponse(
            status_code=400,
            content={"detail": errors}
        )

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Update with frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(BraintrustTracingMiddleware)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
