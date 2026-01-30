"""
Consistent logging configuration for Faux Splunk Cloud.

Provides:
- Structured JSON logging with consistent schema
- Root logger configuration
- Per-module log level configuration
- Request correlation IDs
- Sensitive data masking
"""

import contextvars
import json
import logging
import re
import sys
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# Context variable for request correlation ID
correlation_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)


def get_correlation_id() -> str | None:
    """Get the current correlation ID."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set the correlation ID for the current context."""
    correlation_id_var.set(correlation_id)


# Log event types for categorization
class LogEventType(str, Enum):
    """Standard event types for categorization."""

    # Application lifecycle
    APP_START = "app.start"
    APP_STOP = "app.stop"
    APP_READY = "app.ready"

    # Request handling
    REQUEST_START = "request.start"
    REQUEST_END = "request.end"
    REQUEST_ERROR = "request.error"

    # Authentication
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    AUTH_TOKEN_ISSUED = "auth.token_issued"
    AUTH_TOKEN_EXPIRED = "auth.token_expired"

    # Instance operations
    INSTANCE_CREATE = "instance.create"
    INSTANCE_START = "instance.start"
    INSTANCE_STOP = "instance.stop"
    INSTANCE_DESTROY = "instance.destroy"
    INSTANCE_EXPORT = "instance.export"
    INSTANCE_ERROR = "instance.error"

    # Tenant operations
    TENANT_CREATE = "tenant.create"
    TENANT_UPDATE = "tenant.update"
    TENANT_DELETE = "tenant.delete"
    TENANT_SUSPEND = "tenant.suspend"

    # Service operations
    SERVICE_START = "service.start"
    SERVICE_STOP = "service.stop"
    SERVICE_ERROR = "service.error"
    SERVICE_CONNECT = "service.connect"
    SERVICE_DISCONNECT = "service.disconnect"

    # Docker operations
    DOCKER_PULL = "docker.pull"
    DOCKER_CREATE = "docker.create"
    DOCKER_START = "docker.start"
    DOCKER_STOP = "docker.stop"
    DOCKER_REMOVE = "docker.remove"
    DOCKER_ERROR = "docker.error"

    # SIEM operations
    SIEM_SEARCH = "siem.search"
    SIEM_ALERT = "siem.alert"
    SIEM_REPORT = "siem.report"

    # Impersonation
    IMPERSONATION_START = "impersonation.start"
    IMPERSONATION_END = "impersonation.end"
    IMPERSONATION_REQUEST = "impersonation.request"
    IMPERSONATION_APPROVE = "impersonation.approve"
    IMPERSONATION_REJECT = "impersonation.reject"

    # Generic
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogSchema(BaseModel):
    """
    Consistent schema for all log messages.

    All logged messages conform to this schema for easy parsing
    and analysis in SIEM tools.
    """

    # Required fields
    timestamp: str = Field(
        description="ISO 8601 timestamp in UTC"
    )
    level: str = Field(
        description="Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
    )
    message: str = Field(
        description="Human-readable log message"
    )
    logger: str = Field(
        description="Logger name (module path)"
    )

    # Event categorization
    event_type: str | None = Field(
        default=None,
        description="Categorized event type from LogEventType enum"
    )

    # Request context
    correlation_id: str | None = Field(
        default=None,
        description="Request correlation ID for tracing"
    )
    request_id: str | None = Field(
        default=None,
        description="Unique request identifier"
    )

    # Actor context
    user_id: str | None = Field(
        default=None,
        description="User ID performing the action"
    )
    tenant_id: str | None = Field(
        default=None,
        description="Tenant ID for multi-tenant context"
    )
    impersonated_by: str | None = Field(
        default=None,
        description="Admin user ID if impersonating"
    )

    # Resource context
    resource_type: str | None = Field(
        default=None,
        description="Type of resource (instance, tenant, user, etc.)"
    )
    resource_id: str | None = Field(
        default=None,
        description="ID of the resource"
    )

    # Error context
    error_type: str | None = Field(
        default=None,
        description="Exception class name"
    )
    error_message: str | None = Field(
        default=None,
        description="Exception message"
    )
    stack_trace: str | None = Field(
        default=None,
        description="Full stack trace for errors"
    )

    # Performance metrics
    duration_ms: float | None = Field(
        default=None,
        description="Operation duration in milliseconds"
    )

    # Additional context
    extra: dict[str, Any] | None = Field(
        default=None,
        description="Additional structured data"
    )

    # Source information
    source_file: str | None = Field(
        default=None,
        description="Source file name"
    )
    source_line: int | None = Field(
        default=None,
        description="Source line number"
    )
    source_function: str | None = Field(
        default=None,
        description="Function name"
    )


# Patterns for sensitive data masking
# Order matters - more specific patterns (Bearer) must come before general patterns
SENSITIVE_PATTERNS = [
    # Bearer tokens - full "Authorization: Bearer <token>" pattern
    (re.compile(r'Authorization["\']?\s*[=:]\s*["\']?Bearer\s+[A-Za-z0-9\-_\.]+', re.IGNORECASE), "Authorization: Bearer ***"),
    # Standalone Bearer tokens
    (re.compile(r'Bearer\s+[A-Za-z0-9\-_\.]+', re.IGNORECASE), "Bearer ***"),
    (re.compile(r'password["\']?\s*[=:]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE), "password=***"),
    (re.compile(r'token["\']?\s*[=:]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE), "token=***"),
    (re.compile(r'secret["\']?\s*[=:]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE), "secret=***"),
    (re.compile(r'api_key["\']?\s*[=:]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE), "api_key=***"),
    (re.compile(r'apikey["\']?\s*[=:]\s*["\']?([^"\'\s,}]+)', re.IGNORECASE), "apikey=***"),
    # Generic authorization - only matches non-Bearer authorization values
    (re.compile(r'authorization["\']?\s*[=:]\s*["\']?(?!Bearer)([^"\'\s,}]+)', re.IGNORECASE), "authorization=***"),
]


def mask_sensitive_data(message: str) -> str:
    """Mask sensitive data in log messages."""
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = pattern.sub(replacement, message)
    return message


class StructuredLogFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs.

    Conforms to the LogSchema for consistent parsing.
    """

    def __init__(self, include_source: bool = True, mask_sensitive: bool = True):
        super().__init__()
        self.include_source = include_source
        self.mask_sensitive = mask_sensitive

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as structured JSON."""
        # Mask sensitive data in message
        message = record.getMessage()
        if self.mask_sensitive:
            message = mask_sensitive_data(message)

        # Build the log entry
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": message,
            "logger": record.name,
        }

        # Add correlation ID from context
        correlation_id = get_correlation_id()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in (
                "name", "msg", "args", "created", "filename", "funcName",
                "levelname", "levelno", "lineno", "module", "msecs",
                "pathname", "process", "processName", "relativeCreated",
                "stack_info", "exc_info", "exc_text", "thread", "threadName",
                "message", "getMessage",
            ):
                # Check if it's a known schema field
                if key in LogSchema.model_fields:
                    log_entry[key] = value
                else:
                    extra_fields[key] = value

        if extra_fields:
            log_entry["extra"] = extra_fields

        # Add source information if enabled
        if self.include_source:
            log_entry["source_file"] = record.filename
            log_entry["source_line"] = record.lineno
            log_entry["source_function"] = record.funcName

        # Add exception info if present
        if record.exc_info:
            exc_type, exc_value, exc_tb = record.exc_info
            if exc_type:
                log_entry["error_type"] = exc_type.__name__
            if exc_value:
                log_entry["error_message"] = str(exc_value)
            if record.exc_text:
                log_entry["stack_trace"] = record.exc_text

        return json.dumps(log_entry, default=str)


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for development/console output.

    Includes colors and formatting for better readability.
    """

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True, mask_sensitive: bool = True):
        super().__init__()
        self.use_colors = use_colors
        self.mask_sensitive = mask_sensitive

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record for human readability."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        level = record.levelname
        if self.use_colors and level in self.COLORS:
            level = f"{self.COLORS[level]}{level:8}{self.RESET}"
        else:
            level = f"{level:8}"

        message = record.getMessage()
        if self.mask_sensitive:
            message = mask_sensitive_data(message)

        # Build base message
        output = f"{timestamp} | {level} | {record.name:40} | {message}"

        # Add correlation ID if present
        correlation_id = get_correlation_id()
        if correlation_id:
            output = f"{timestamp} | {level} | [{correlation_id[:8]}] {record.name:30} | {message}"

        # Add exception info if present
        if record.exc_info:
            import traceback
            output += "\n" + "".join(traceback.format_exception(*record.exc_info))

        return output


class StructuredLogger(logging.Logger):
    """
    Enhanced logger that supports structured logging.

    Provides convenience methods for logging with schema-compliant fields.
    """

    def _log_with_extras(
        self,
        level: int,
        msg: str,
        event_type: LogEventType | str | None = None,
        user_id: str | None = None,
        tenant_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        duration_ms: float | None = None,
        extra: dict[str, Any] | None = None,
        exc_info: bool = False,
        **kwargs,
    ):
        """Log with structured extra fields."""
        extra_dict = extra or {}

        if event_type:
            extra_dict["event_type"] = event_type if isinstance(event_type, str) else event_type.value
        if user_id:
            extra_dict["user_id"] = user_id
        if tenant_id:
            extra_dict["tenant_id"] = tenant_id
        if resource_type:
            extra_dict["resource_type"] = resource_type
        if resource_id:
            extra_dict["resource_id"] = resource_id
        if duration_ms is not None:
            extra_dict["duration_ms"] = duration_ms

        self.log(level, msg, exc_info=exc_info, extra=extra_dict, **kwargs)

    def event(
        self,
        event_type: LogEventType | str,
        msg: str,
        level: int = logging.INFO,
        **kwargs,
    ):
        """Log a categorized event."""
        self._log_with_extras(level, msg, event_type=event_type, **kwargs)

    def request_start(
        self,
        method: str,
        path: str,
        user_id: str | None = None,
        tenant_id: str | None = None,
    ):
        """Log request start."""
        self.event(
            LogEventType.REQUEST_START,
            f"{method} {path}",
            user_id=user_id,
            tenant_id=tenant_id,
        )

    def request_end(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        user_id: str | None = None,
        tenant_id: str | None = None,
    ):
        """Log request end."""
        self.event(
            LogEventType.REQUEST_END,
            f"{method} {path} -> {status_code}",
            duration_ms=duration_ms,
            user_id=user_id,
            tenant_id=tenant_id,
            extra={"status_code": status_code},
        )

    def instance_event(
        self,
        event_type: LogEventType,
        instance_id: str,
        msg: str | None = None,
        **kwargs,
    ):
        """Log an instance-related event."""
        message = msg or f"Instance {event_type.value}"
        self.event(
            event_type,
            message,
            resource_type="instance",
            resource_id=instance_id,
            **kwargs,
        )

    def service_event(
        self,
        event_type: LogEventType,
        service_name: str,
        msg: str | None = None,
        **kwargs,
    ):
        """Log a service-related event."""
        message = msg or f"Service {event_type.value}"
        self.event(
            event_type,
            message,
            resource_type="service",
            resource_id=service_name,
            **kwargs,
        )

    def auth_event(
        self,
        event_type: LogEventType,
        user_id: str | None = None,
        msg: str | None = None,
        **kwargs,
    ):
        """Log an authentication event."""
        message = msg or f"Auth {event_type.value}"
        self.event(
            event_type,
            message,
            user_id=user_id,
            resource_type="auth",
            **kwargs,
        )


# Module-level configuration
class LogConfig(BaseModel):
    """Configuration for the logging system."""

    # Global settings
    level: str = Field(default="INFO", description="Default log level")
    format: str = Field(default="json", description="Output format: 'json' or 'human'")
    include_source: bool = Field(default=True, description="Include source file/line info")
    mask_sensitive: bool = Field(default=True, description="Mask passwords and tokens")
    use_colors: bool = Field(default=True, description="Use colors in human format")

    # Per-module log levels (overrides default)
    module_levels: dict[str, str] = Field(
        default_factory=lambda: {
            "uvicorn": "INFO",
            "uvicorn.access": "WARNING",
            "uvicorn.error": "INFO",
            "fastapi": "INFO",
            "httpx": "WARNING",
            "docker": "WARNING",
            "sqlalchemy.engine": "WARNING",
            "faux_splunk_cloud": "INFO",
            "faux_splunk_cloud.services": "INFO",
            "faux_splunk_cloud.api": "INFO",
        },
        description="Per-module log level overrides"
    )


def configure_logging(config: LogConfig | None = None) -> None:
    """
    Configure the root logger and all module loggers.

    Call this once at application startup.
    """
    if config is None:
        config = LogConfig()

    # Register custom logger class
    logging.setLoggerClass(StructuredLogger)

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Allow all, filter at handler level

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(getattr(logging, config.level.upper()))

    # Set formatter based on config
    if config.format == "json":
        formatter = StructuredLogFormatter(
            include_source=config.include_source,
            mask_sensitive=config.mask_sensitive,
        )
    else:
        formatter = HumanReadableFormatter(
            use_colors=config.use_colors,
            mask_sensitive=config.mask_sensitive,
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Configure per-module log levels
    for module, level in config.module_levels.items():
        module_logger = logging.getLogger(module)
        module_logger.setLevel(getattr(logging, level.upper()))


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger for the given module.

    Usage:
        from faux_splunk_cloud.logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Hello world")
        logger.event(LogEventType.INSTANCE_CREATE, "Created instance", instance_id="xyz")
    """
    return logging.getLogger(name)  # type: ignore


# Convenience function for getting module logger
def getLogger(name: str) -> StructuredLogger:
    """Alias for get_logger (matches logging module API)."""
    return get_logger(name)
