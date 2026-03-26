"""Global exception handlers for the FastAPI application.

Centralises error-to-HTTP-response mapping so that:
- Domain exceptions from the service layer produce consistent JSON responses
  without repetitive try/except blocks in every route handler.
- Database constraint violations return 409 instead of a raw 500.
- Truly unexpected errors are logged with full tracebacks but only a
  sanitised message is returned to the client.
"""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Handler implementations
# ---------------------------------------------------------------------------

async def _order_not_found_handler(
    request: Request, exc: Exception,
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Order not found"})


async def _invalid_sort_handler(
    request: Request, exc: Exception,
) -> JSONResponse:
    # The message is developer-controlled (e.g. "Invalid sort_by. Must be
    # one of: …"), so it is safe to forward.
    return JSONResponse(status_code=422, content={"detail": str(exc)})


async def _integrity_error_handler(
    request: Request, exc: IntegrityError,
) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "A conflicting record already exists"},
    )


async def _unhandled_exception_handler(
    request: Request, exc: Exception,
) -> JSONResponse:
    logger.error(
        "Unhandled exception on %s %s",
        request.method,
        request.url.path,
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI app.

    Handler lookup follows the exception MRO, so more specific handlers
    (e.g. OrderNotFoundError) are matched before the generic Exception
    fallback.  Built-in FastAPI handlers for HTTPException and
    RequestValidationError remain unaffected.
    """
    from app.services.orders.order_service import OrderNotFoundError, InvalidSortError

    app.add_exception_handler(OrderNotFoundError, _order_not_found_handler)
    app.add_exception_handler(InvalidSortError, _invalid_sort_handler)
    app.add_exception_handler(IntegrityError, _integrity_error_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
