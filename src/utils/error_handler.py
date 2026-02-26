"""Graceful error handling for API failures with user-friendly messages."""
from __future__ import annotations

import sys
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)


class APIError(Exception):
    """Base class for API-related errors with user-friendly messaging."""
    
    def __init__(self, error_type: str, message: str, details: str = "", is_retryable: bool = False):
        self.error_type = error_type
        self.message = message
        self.details = details
        self.is_retryable = is_retryable
        super().__init__(self.message)
    
    def get_user_message(self) -> str:
        """Return a user-friendly error message."""
        msg = f"\n❌ {self.message}"
        if self.details:
            msg += f"\n   Details: {self.details}"
        if self.is_retryable:
            msg += "\n   💡 Tip: This is a temporary issue. Please retry in a few moments."
        return msg


class OverloadedError(APIError):
    """Claude API is overloaded (HTTP 529)."""
    
    def __init__(self, request_id: str = ""):
        super().__init__(
            error_type="API_OVERLOADED",
            message="Claude API is currently overloaded",
            details=f"Request ID: {request_id}" if request_id else "The service is at capacity",
            is_retryable=True
        )


class RateLimitError(APIError):
    """Claude API rate limit exceeded (HTTP 429)."""
    
    def __init__(self, retry_after: Optional[int] = None):
        details = f"Retry after {retry_after} seconds" if retry_after else "Rate limit exceeded"
        super().__init__(
            error_type="RATE_LIMIT",
            message="Claude API rate limit exceeded",
            details=details,
            is_retryable=True
        )


class AuthenticationError(APIError):
    """Authentication failed (HTTP 401/403)."""
    
    def __init__(self):
        super().__init__(
            error_type="AUTH_FAILED",
            message="Authentication failed - check your ANTHROPIC_API_KEY",
            details="Ensure ANTHROPIC_API_KEY environment variable is set correctly",
            is_retryable=False
        )


class InvalidResponseError(APIError):
    """Claude returned invalid or empty response."""
    
    def __init__(self, response_type: str = ""):
        super().__init__(
            error_type="INVALID_RESPONSE",
            message=f"Claude returned invalid response{f' ({response_type})' if response_type else ''}",
            details="The API response could not be parsed. This may be a temporary issue.",
            is_retryable=True
        )


class SchemaValidationError(APIError):
    """Response failed schema validation."""
    
    def __init__(self, validation_error: str):
        super().__init__(
            error_type="SCHEMA_VALIDATION",
            message="Claude response failed schema validation",
            details=f"Validation error: {validation_error}",
            is_retryable=True
        )


def handle_anthropic_error(error: Exception) -> APIError:
    """Convert Anthropic SDK exceptions to user-friendly APIError."""
    error_str = str(error)
    error_type = type(error).__name__
    
    # Check for specific error codes
    if "529" in error_str or "overloaded" in error_str.lower():
        request_id = ""
        if "request_id" in error_str:
            try:
                request_id = error_str.split("request_id': '")[1].split("'")[0]
            except (IndexError, ValueError):
                pass
        return OverloadedError(request_id)
    
    elif "429" in error_str or "rate_limit" in error_str.lower():
        retry_after = None
        if "retry_after" in error_str:
            try:
                retry_after = int(error_str.split("retry_after")[1].split()[0])
            except (IndexError, ValueError):
                pass
        return RateLimitError(retry_after)
    
    elif "401" in error_str or "403" in error_str or "authentication" in error_str.lower():
        return AuthenticationError()
    
    elif "json" in error_str.lower() or "parse" in error_str.lower():
        return InvalidResponseError("JSON parsing")
    
    # Generic API error
    return APIError(
        error_type=error_type,
        message="Claude API request failed",
        details=error_str[:200],  # Truncate long error messages
        is_retryable="timeout" in error_str.lower() or "connection" in error_str.lower()
    )


def exit_with_error(error: APIError, context: str = "") -> int:
    """Log error and exit gracefully with user-friendly message."""
    logger.error(
        "pipeline_failed",
        error_type=error.error_type,
        message=error.message,
        details=error.details,
        context=context,
    )
    
    print(error.get_user_message(), file=sys.stderr)
    
    if error.is_retryable:
        print("\n📋 Next steps:", file=sys.stderr)
        print("   1. Wait a moment for the service to recover", file=sys.stderr)
        print("   2. Run the same command again", file=sys.stderr)
    else:
        print("\n📋 Next steps:", file=sys.stderr)
        print("   1. Check your ANTHROPIC_API_KEY environment variable", file=sys.stderr)
        print("   2. Verify you have access to Claude API", file=sys.stderr)
    
    print("", file=sys.stderr)
    return 1
