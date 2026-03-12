"""
Standardized Error Response Format for ag3ntwerk.

Provides consistent error responses across the entire API:
- Standard error structure
- Error codes
- HTTP status mapping
- Request ID correlation
- Structured error details

Usage:
    from ag3ntwerk.core.errors import (
        ErrorResponse,
        ErrorCode,
        create_error_response,
        error_handler,
    )

    # Create an error response
    error = create_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message="Invalid task type",
        details={"field": "task_type", "value": "invalid"},
    )

    # Use as exception handler
    @app.exception_handler(ValueError)
    async def value_error_handler(request, exc):
        return error_handler(request, exc)
"""

import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Standard error codes."""

    # General errors (1xxx)
    INTERNAL_ERROR = "E1000"
    UNKNOWN_ERROR = "E1001"
    SERVICE_UNAVAILABLE = "E1002"
    MAINTENANCE_MODE = "E1003"

    # Validation errors (2xxx)
    VALIDATION_ERROR = "E2000"
    INVALID_INPUT = "E2001"
    MISSING_REQUIRED_FIELD = "E2002"
    INVALID_FORMAT = "E2003"
    VALUE_OUT_OF_RANGE = "E2004"
    INVALID_TASK_TYPE = "E2005"
    INVALID_PRIORITY = "E2006"

    # Authentication/Authorization errors (3xxx)
    UNAUTHORIZED = "E3000"
    FORBIDDEN = "E3001"
    INVALID_TOKEN = "E3002"
    TOKEN_EXPIRED = "E3003"
    INSUFFICIENT_PERMISSIONS = "E3004"

    # Resource errors (4xxx)
    NOT_FOUND = "E4000"
    RESOURCE_NOT_FOUND = "E4001"
    TASK_NOT_FOUND = "E4002"
    WORKFLOW_NOT_FOUND = "E4003"
    AGENT_NOT_FOUND = "E4004"
    MODEL_NOT_FOUND = "E4005"

    # Rate limiting errors (5xxx)
    RATE_LIMITED = "E5000"
    TOO_MANY_REQUESTS = "E5001"
    QUOTA_EXCEEDED = "E5002"

    # LLM errors (6xxx)
    LLM_ERROR = "E6000"
    LLM_CONNECTION_ERROR = "E6001"
    LLM_TIMEOUT = "E6002"
    LLM_RESPONSE_ERROR = "E6003"
    LLM_OVERLOADED = "E6004"

    # Task errors (7xxx)
    TASK_ERROR = "E7000"
    TASK_EXECUTION_ERROR = "E7001"
    TASK_TIMEOUT = "E7002"
    TASK_CANCELLED = "E7003"

    # Workflow errors (8xxx)
    WORKFLOW_ERROR = "E8000"
    WORKFLOW_EXECUTION_ERROR = "E8001"
    WORKFLOW_STEP_FAILED = "E8002"

    # Configuration errors (9xxx)
    CONFIGURATION_ERROR = "E9000"
    INVALID_CONFIGURATION = "E9001"


# HTTP status code mapping
ERROR_STATUS_CODES: Dict[ErrorCode, int] = {
    # 400 Bad Request
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.MISSING_REQUIRED_FIELD: 400,
    ErrorCode.INVALID_FORMAT: 400,
    ErrorCode.VALUE_OUT_OF_RANGE: 400,
    ErrorCode.INVALID_TASK_TYPE: 400,
    ErrorCode.INVALID_PRIORITY: 400,
    ErrorCode.INVALID_CONFIGURATION: 400,
    # 401 Unauthorized
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.INVALID_TOKEN: 401,
    ErrorCode.TOKEN_EXPIRED: 401,
    # 403 Forbidden
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.INSUFFICIENT_PERMISSIONS: 403,
    # 404 Not Found
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.RESOURCE_NOT_FOUND: 404,
    ErrorCode.TASK_NOT_FOUND: 404,
    ErrorCode.WORKFLOW_NOT_FOUND: 404,
    ErrorCode.AGENT_NOT_FOUND: 404,
    ErrorCode.MODEL_NOT_FOUND: 404,
    # 429 Too Many Requests
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.TOO_MANY_REQUESTS: 429,
    ErrorCode.QUOTA_EXCEEDED: 429,
    # 500 Internal Server Error
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.UNKNOWN_ERROR: 500,
    ErrorCode.TASK_ERROR: 500,
    ErrorCode.TASK_EXECUTION_ERROR: 500,
    ErrorCode.WORKFLOW_ERROR: 500,
    ErrorCode.WORKFLOW_EXECUTION_ERROR: 500,
    ErrorCode.WORKFLOW_STEP_FAILED: 500,
    ErrorCode.CONFIGURATION_ERROR: 500,
    # 502 Bad Gateway
    ErrorCode.LLM_ERROR: 502,
    ErrorCode.LLM_CONNECTION_ERROR: 502,
    ErrorCode.LLM_RESPONSE_ERROR: 502,
    # 503 Service Unavailable
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.MAINTENANCE_MODE: 503,
    ErrorCode.LLM_OVERLOADED: 503,
    # 504 Gateway Timeout
    ErrorCode.LLM_TIMEOUT: 504,
    ErrorCode.TASK_TIMEOUT: 504,
    # 499 Client Closed Request (custom)
    ErrorCode.TASK_CANCELLED: 499,
}


class ErrorDetail(BaseModel):
    """Additional error details."""

    field: Optional[str] = Field(default=None, description="Field that caused the error")
    value: Optional[Any] = Field(default=None, description="Invalid value")
    constraint: Optional[str] = Field(default=None, description="Violated constraint")
    suggestion: Optional[str] = Field(default=None, description="Suggested fix")


class ErrorResponse(BaseModel):
    """
    Standard error response format.

    All API errors should return this structure.
    """

    error: bool = Field(default=True, description="Always true for errors")
    code: str = Field(..., description="Error code (e.g., E1000)")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[List[ErrorDetail]] = Field(
        default=None,
        description="Additional error details",
    )
    request_id: Optional[str] = Field(
        default=None,
        description="Request ID for tracking",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Error timestamp",
    )
    path: Optional[str] = Field(default=None, description="Request path")
    method: Optional[str] = Field(default=None, description="HTTP method")

    # Debug info (only in development)
    debug: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Debug information (development only)",
    )


def create_error_response(
    code: ErrorCode,
    message: str,
    details: Optional[List[Dict[str, Any]]] = None,
    request_id: Optional[str] = None,
    path: Optional[str] = None,
    method: Optional[str] = None,
    debug: Optional[Dict[str, Any]] = None,
    include_debug: bool = False,
) -> ErrorResponse:
    """
    Create a standardized error response.

    Args:
        code: Error code
        message: Human-readable message
        details: List of error details
        request_id: Request ID for correlation
        path: Request path
        method: HTTP method
        debug: Debug information
        include_debug: Whether to include debug info

    Returns:
        ErrorResponse object
    """
    error_details = None
    if details:
        error_details = [ErrorDetail(**d) for d in details]

    return ErrorResponse(
        code=code.value,
        message=message,
        details=error_details,
        request_id=request_id,
        path=path,
        method=method,
        debug=debug if include_debug else None,
    )


def create_json_response(
    error_response: ErrorResponse,
    status_code: Optional[int] = None,
) -> JSONResponse:
    """
    Create a JSONResponse from an ErrorResponse.

    Args:
        error_response: The error response
        status_code: Optional status code override

    Returns:
        JSONResponse with proper status code
    """
    # Determine status code
    if status_code is None:
        code_enum = None
        for ec in ErrorCode:
            if ec.value == error_response.code:
                code_enum = ec
                break
        status_code = ERROR_STATUS_CODES.get(code_enum, 500) if code_enum else 500

    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(exclude_none=True),
    )


def get_request_info(request: Request) -> Dict[str, Any]:
    """Extract request information for error responses."""
    request_id = ""
    try:
        from ag3ntwerk.api.app import get_request_id

        request_id = get_request_id()
    except ImportError:
        request_id = getattr(request.state, "request_id", "")

    return {
        "request_id": request_id,
        "path": str(request.url.path),
        "method": request.method,
    }


# Exception to Error Code mapping
EXCEPTION_MAPPINGS: Dict[Type[Exception], ErrorCode] = {}


def register_exception_mapping(exception_type: Type[Exception], code: ErrorCode) -> None:
    """Register an exception type to error code mapping."""
    EXCEPTION_MAPPINGS[exception_type] = code


def get_error_code_for_exception(exc: Exception) -> ErrorCode:
    """Get the appropriate error code for an exception."""
    for exc_type, code in EXCEPTION_MAPPINGS.items():
        if isinstance(exc, exc_type):
            return code
    return ErrorCode.INTERNAL_ERROR


def exception_to_error_response(
    exc: Exception,
    request: Optional[Request] = None,
    include_debug: bool = False,
) -> ErrorResponse:
    """
    Convert an exception to an ErrorResponse.

    Args:
        exc: The exception
        request: Optional request for context
        include_debug: Include debug information

    Returns:
        ErrorResponse
    """
    code = get_error_code_for_exception(exc)

    # Get request info
    request_info = {}
    if request:
        request_info = get_request_info(request)

    # Build debug info
    debug = None
    if include_debug:
        debug = {
            "exception_type": type(exc).__name__,
            "traceback": traceback.format_exc(),
        }

    return create_error_response(
        code=code,
        message=str(exc),
        request_id=request_info.get("request_id"),
        path=request_info.get("path"),
        method=request_info.get("method"),
        debug=debug,
        include_debug=include_debug,
    )


async def generic_exception_handler(
    request: Request,
    exc: Exception,
    include_debug: bool = False,
) -> JSONResponse:
    """
    Generic exception handler for FastAPI.

    Usage:
        @app.exception_handler(Exception)
        async def handle_exception(request, exc):
            return await generic_exception_handler(request, exc)
    """
    error_response = exception_to_error_response(exc, request, include_debug)

    # Log the error
    logger.error(
        "Request failed with exception: %s [%s] path=%s request_id=%s",
        error_response.message,
        error_response.code,
        error_response.path,
        error_response.request_id,
        exc_info=True,
    )

    return create_json_response(error_response)


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    """
    Handler for FastAPI HTTPException.

    Converts HTTPException to standardized error format.
    """
    # Map HTTP status to error code
    status_code_mapping = {
        400: ErrorCode.VALIDATION_ERROR,
        401: ErrorCode.UNAUTHORIZED,
        403: ErrorCode.FORBIDDEN,
        404: ErrorCode.NOT_FOUND,
        429: ErrorCode.RATE_LIMITED,
        500: ErrorCode.INTERNAL_ERROR,
        502: ErrorCode.LLM_ERROR,
        503: ErrorCode.SERVICE_UNAVAILABLE,
        504: ErrorCode.LLM_TIMEOUT,
    }

    code = status_code_mapping.get(exc.status_code, ErrorCode.INTERNAL_ERROR)
    request_info = get_request_info(request)

    error_response = create_error_response(
        code=code,
        message=str(exc.detail),
        request_id=request_info.get("request_id"),
        path=request_info.get("path"),
        method=request_info.get("method"),
    )

    return create_json_response(error_response, status_code=exc.status_code)


async def validation_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handler for Pydantic validation errors.
    """
    from pydantic import ValidationError

    if not isinstance(exc, ValidationError):
        return await generic_exception_handler(request, exc)

    request_info = get_request_info(request)
    details = []

    for error in exc.errors():
        details.append(
            {
                "field": ".".join(str(loc) for loc in error["loc"]),
                "value": error.get("input"),
                "constraint": error["type"],
                "suggestion": error["msg"],
            }
        )

    error_response = create_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed",
        details=details,
        request_id=request_info.get("request_id"),
        path=request_info.get("path"),
        method=request_info.get("method"),
    )

    return create_json_response(error_response)


# Register ag3ntwerk exception mappings
def register_exceptions() -> None:
    """Register mappings for ag3ntwerk custom exceptions."""
    try:
        from ag3ntwerk.core.exceptions import (
            TaskExecutionError,
            TaskTimeoutError,
            TaskCancelledError,
            TaskValidationError,
            LLMConnectionError,
            LLMTimeoutError,
            LLMModelNotFoundError,
            LLMResponseError,
            ConfigurationError,
        )

        register_exception_mapping(TaskExecutionError, ErrorCode.TASK_EXECUTION_ERROR)
        register_exception_mapping(TaskTimeoutError, ErrorCode.TASK_TIMEOUT)
        register_exception_mapping(TaskCancelledError, ErrorCode.TASK_CANCELLED)
        register_exception_mapping(TaskValidationError, ErrorCode.VALIDATION_ERROR)
        register_exception_mapping(LLMConnectionError, ErrorCode.LLM_CONNECTION_ERROR)
        register_exception_mapping(LLMTimeoutError, ErrorCode.LLM_TIMEOUT)
        register_exception_mapping(LLMModelNotFoundError, ErrorCode.MODEL_NOT_FOUND)
        register_exception_mapping(LLMResponseError, ErrorCode.LLM_RESPONSE_ERROR)
        register_exception_mapping(ConfigurationError, ErrorCode.CONFIGURATION_ERROR)

    except ImportError:
        pass

    # Standard exceptions
    register_exception_mapping(ValueError, ErrorCode.VALIDATION_ERROR)
    register_exception_mapping(TypeError, ErrorCode.VALIDATION_ERROR)
    register_exception_mapping(KeyError, ErrorCode.NOT_FOUND)
    register_exception_mapping(TimeoutError, ErrorCode.TASK_TIMEOUT)


# Register on import
register_exceptions()


__all__ = [
    # Response classes
    "ErrorResponse",
    "ErrorDetail",
    # Error codes
    "ErrorCode",
    "ERROR_STATUS_CODES",
    # Functions
    "create_error_response",
    "create_json_response",
    "exception_to_error_response",
    "get_error_code_for_exception",
    "get_request_info",
    "register_exception_mapping",
    # Exception handlers
    "generic_exception_handler",
    "http_exception_handler",
    "validation_exception_handler",
    "register_exceptions",
]
