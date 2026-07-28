import os
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import braintrust

logger = logging.getLogger(__name__)

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
