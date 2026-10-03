"""FastAPI Application Factory for Ocean Sentinel V1."""

from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ocean_sentinel.api.routes import router

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance."""
    app = FastAPI(
        title="Ocean Sentinel Backend API",
        description=(
            "Machine-readable HTTP API and pipeline orchestrator for satellite-based "
            "oil spill detection, drift origin analysis, AIS correlation, and multi-source evidence fusion. "
            "Establishes spatio-temporal compatibility only; does NOT assign legal attribution."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Configure CORS for local development and future frontend integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # -----------------------------------------------------------------------
    # Error Handlers
    # -----------------------------------------------------------------------

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Handle request parameter validation errors with canonical ErrorResponse shape."""
        errors: list[Dict[str, Any]] = []
        for err in exc.errors():
            errors.append({
                "loc": err.get("loc"),
                "msg": err.get("msg"),
                "type": err.get("type"),
            })

        return JSONResponse(
            status_code=422,
            content={
                "code": "INVALID_INPUT",
                "message": "Request validation failed.",
                "stage": "VALIDATE",
                "retryable": False,
                "details": {"validation_errors": errors},
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        """Standardize HTTPException format into ErrorResponse schema."""
        detail = exc.detail
        if isinstance(detail, dict):
            content = {
                "code": detail.get("code", "HTTP_ERROR"),
                "message": detail.get("message", str(detail)),
                "stage": detail.get("stage"),
                "retryable": detail.get("retryable", False),
                "details": detail.get("details", {}),
            }
        else:
            content = {
                "code": "HTTP_ERROR",
                "message": str(detail),
                "stage": None,
                "retryable": False,
                "details": {},
            }
        return JSONResponse(status_code=exc.status_code, content=content)

    # Mount versioned API routes
    app.include_router(router)

    return app
