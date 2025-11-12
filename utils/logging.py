import re
import logging


class SanitizationFilter(logging.Filter):
    """
    A logging filter that sanitizes log messages to prevent log injection.
    Automatically removes control characters, ANSI escape sequences, and truncates long messages.
    """

    def __init__(self, max_length=1000):
        super().__init__()
        self.max_length = max_length

    def filter(self, record):
        """Filter and sanitize the log record."""
        # Sanitize any string arguments first
        if hasattr(record, "args") and record.args:
            sanitized_args = tuple(
                self._sanitize_value(arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
            record.args = sanitized_args

        # Sanitize the main message
        if hasattr(record, "msg"):
            record.msg = self._sanitize_value(record.msg)

        # Override getMessage to return sanitized message
        if hasattr(record, "getMessage"):
            original_get_message = record.getMessage

            def get_sanitized_message():
                message = original_get_message()
                return self._sanitize_value(message)

            record.getMessage = get_sanitized_message

        return True

    def _sanitize_value(self, value):
        """
        Sanitize a value to prevent log injection.

        Args:
            value: The value to sanitize (can be any type)

        Returns:
            A safe string for logging
        """
        if value is None:
            return "None"

        # Convert to string
        str_value = str(value)

        # Truncate to max_length to prevent log flooding
        if len(str_value) > self.max_length:
            str_value = str_value[: self.max_length] + "...[truncated]"

        # Remove control characters that could cause log injection
        # Remove \r, \n, \t and other control characters
        str_value = re.sub(r"[\r\n\t\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", str_value)

        # Remove potential ANSI escape sequences used for terminal control
        str_value = re.sub(r"\x1B\[[0-9;]*[mK]", "", str_value)

        return str_value


def add_sanitization_to_logger(logger, max_length=1000):
    """
    Add sanitization filter to a logger instance.

    Args:
        logger: The logger instance to add the filter to
        max_length: Maximum length for log messages
    """
    sanitization_filter = SanitizationFilter(max_length)
    logger.addFilter(sanitization_filter)
    return logger
