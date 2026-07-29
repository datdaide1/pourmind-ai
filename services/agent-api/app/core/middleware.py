import asyncio
from collections import defaultdict, deque
import os
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import braintrust

from starlette.responses import JSONResponse
logger = logging.getLogger(__name__)
from app.core.config import settings

class ApiProtectionMiddleware(BaseHTTPMiddleware):
    """Bound request bodies and apply a per-process IP rate-limit safety net."""

    def __init__(self, app):
        super().__init__(app)
        self._requests = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/api/v1"):
            return await call_next(request)
        content_length = request.headers.get("content-length")
        if content_length:
            try:
                if int(content_length) > settings.MAX_REQUEST_BODY_BYTES:
                    return JSONResponse(status_code=413, content={"detail": "Request body too large"})
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length"})
        body = await request.body()
        if len(body) > settings.MAX_REQUEST_BODY_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Request body too large"})

        client_key = request.client.host if request.client else "unknown"
        now = time.monotonic()
        async with self._lock:
            recent = self._requests[client_key]
            cutoff = now - settings.API_RATE_LIMIT_WINDOW_SECONDS
            while recent and recent[0] <= cutoff:
                recent.popleft()
            if len(recent) >= settings.API_RATE_LIMIT_REQUESTS:
                return JSONResponse(status_code=429, content={"detail": "API rate limit exceeded"})
            recent.append(now)
        return await call_next(request)
class BraintrustTracingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        # Intercept only API requests under '/api/v1'
        if not request.url.path.startswith("/api/v1"):
            return await call_next(request)

        # Fail gracefully if BRAINTRUST_API_KEY is not set
        if not os.environ.get("BRAINTRUST_API_KEY"):
            logger.debug("BRAINTRUST_API_KEY not set. Skipping Braintrust tracing.")
            return await call_next(request)

        try:
            braintrust.init_logger(project="PourMind-AI")
        except Exception as e:
            logger.debug(f"Failed to initialize Braintrust logger: {e}")
            # Do not break request lifecycle: proceed without tracing if logging init fails
            return await call_next(request)

        method = request.method
        path = request.url.path
        query_params = dict(request.query_params)
        
        span = None
        start_time = time.time()
        
        try:
            span = braintrust.start_span(name=f"{method} {path}")
        except Exception as e:
            logger.debug(f"Failed to start Braintrust span: {e}")

        status_code = None
        error_msg = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as e:
            error_msg = str(e)
            raise e
        finally:
            duration = time.time() - start_time
            if span:
                try:
                    span.log(
                        input={
                            "method": method,
                            "path": path,
                            "query_params": query_params,
                        },
                        output={
                            "status_code": status_code,
                            "error": error_msg,
                        },
                        metadata={
                            "duration": duration,
                            "status_code": status_code,
                            "error": error_msg,
                        }
                    )
                except Exception as log_ex:
                    logger.debug(f"Failed to log to Braintrust span: {log_ex}")
                finally:
                    try:
                        span.close()
                    except Exception as close_ex:
                        logger.debug(f"Failed to close Braintrust span: {close_ex}")
