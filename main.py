import logging
import traceback
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import settings, validate_secret_key
from app.api import (
    auth,
    users,
    staff,
    providers,
    bikes,
    requests as service_requests,
    jobs,
    estimates,
    files,
    invoices,
    reports,
    feedback,
    assistant,
    audit,
    security_events,
)

logger = logging.getLogger("bikecare")
logging.basicConfig(level=logging.INFO)

# Validate configuration on startup
validate_secret_key()

# Setup rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT_GLOBAL])

docs_url = None if settings.is_production() else "/docs"
redoc_url = None if settings.is_production() else "/redoc"
openapi_url = None if settings.is_production() else "/openapi.json"

app = FastAPI(
    title="BikeCare API",
    description="Smart Bike Service Management Platform Backend",
    version="1.0.0",
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# Custom Security Headers & Request ID Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Enforce maximum body size (1 MB for standard JSON requests)
        content_length = request.headers.get("content-length")
        is_upload = request.url.path.endswith("/attachments")
        max_bytes = 10 * 1024 * 1024 if is_upload else 1024 * 1024
        if content_length and int(content_length) > max_bytes:
            return JSONResponse(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                content={
                    "error": {
                        "code": "PAYLOAD_TOO_LARGE",
                        "message": f"Payload size exceeds allowed limit ({max_bytes} bytes).",
                        "request_id": str(uuid.uuid4())
                    }
                }
            )

        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        response = await call_next(request)

        # Apply security headers to every response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

        if request.url.path.startswith("/api/"):
            # Disable caching of private API endpoints
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"

        if settings.is_production():
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Suppress server signature header
        if "server" in response.headers:
            del response.headers["server"]

        return response


app.add_middleware(SecurityHeadersMiddleware)

# Trusted Hosts
allowed_hosts = settings.get_allowed_hosts()
if allowed_hosts:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# Strict CORS configuration
origins = settings.get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With", "X-Request-ID"],
)


# Global Exception Handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    logger.error(f"[Req {req_id}] Unhandled error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred. Please contact support with this request ID.",
                "request_id": req_id
            }
        },
        headers={"X-Request-ID": req_id}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    # Sanitize validation errors to not echo sensitive fields
    errors = []
    for err in exc.errors():
        loc = [str(x) for x in err.get("loc", [])]
        loc_str = " -> ".join(loc)
        # Never reflect password or token values
        if any(s in loc_str.lower() for s in ["password", "token", "secret"]):
            msg = "Invalid value for sensitive field."
        else:
            msg = err.get("msg", "Invalid value.")
        errors.append(f"{loc_str}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "; ".join(errors),
                "request_id": req_id
            }
        },
        headers={"X-Request-ID": req_id}
    )


# Include all API routers under /api
api_prefix = "/api"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(users.router, prefix=api_prefix)
app.include_router(staff.router, prefix=api_prefix)
app.include_router(providers.router, prefix=api_prefix)
app.include_router(bikes.router, prefix=api_prefix)
app.include_router(service_requests.router, prefix=api_prefix)
app.include_router(jobs.router, prefix=api_prefix)
app.include_router(estimates.router, prefix=api_prefix)
app.include_router(files.router, prefix=api_prefix)
app.include_router(invoices.router, prefix=api_prefix)
app.include_router(reports.router, prefix=api_prefix)
app.include_router(feedback.router, prefix=api_prefix)
app.include_router(assistant.router, prefix=api_prefix)
app.include_router(audit.router, prefix=api_prefix)
app.include_router(security_events.router, prefix=api_prefix)


import subprocess
from sqlalchemy import text

@app.on_event("startup")
async def startup_log():
    if settings.APP_ENV.lower() == "test":
        return
    from app.db.session import engine
    db_url = settings.get_database_url()
    masked = db_url[:db_url.find('://')+3] + '***:***@' + db_url[db_url.rfind('@')+1:] if '@' in db_url else db_url
    logger.info(f"BikeCare starting up | ENV={settings.APP_ENV} | DB={masked}")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("Database connectivity: OK")
    except Exception as e:
        logger.error(f"Database connectivity FAILED: {e}")


@app.get("/api/health", tags=["system"])
def health_check():
    from app.db.session import engine
    db_ok = False
    db_error = None
    alembic_rev = None
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
        # Get current alembic revision
        try:
            from alembic.runtime.migration import MigrationContext
            from alembic.config import Config
            import os
            alembic_cfg_path = os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
            with engine.connect() as conn:
                ctx = MigrationContext.configure(conn)
                alembic_rev = ctx.get_current_revision()
        except Exception:
            alembic_rev = "unknown"
    except Exception as e:
        db_error = str(e)

    return {
        "status": "healthy" if db_ok else "degraded",
        "app": "BikeCare",
        "env": settings.APP_ENV,
        "database": {
            "connected": db_ok,
            "type": "sqlite" if "sqlite" in settings.get_database_url() else "postgresql",
            "error": db_error
        },
        "migration_revision": alembic_rev
    }


# Mount frontend directory for unified single-port access
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
