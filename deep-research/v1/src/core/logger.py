import json
import logging
from typing import Literal

from config import get_settings


CONSOLE_LOG_FORMAT = "%(asctime)s - %(levelname)s - [%(pathname)s:%(lineno)s - %(funcName)s] - %(message)s"

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

settings = get_settings()


class ConsoleFormatter(logging.Formatter):
    _COLORS = {
        "DEBUG": "\033[36m",  # CYAN
        "INFO": "\033[32m",  # GREEN
        "WARNING": "\033[33m",  # YELLOW
        "ERROR": "\033[31m",  # RED
        "CRITICAL": "\033[1;31m",  # BOLD RED
    }
    _RESET = "\033[0m"

    def __init__(self, fmt: str = CONSOLE_LOG_FORMAT, datefmt: str | None = None):
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        if record.name.startswith("sqlalchemy"):
            return record.getMessage()
        else:
            return self._format_general_record(record)

    def _format_general_record(self, record: logging.LogRecord) -> str:
        log_color = self._COLORS.get(record.levelname, self._RESET)
        debug_color = self._COLORS["DEBUG"]

        original_levelname = record.levelname
        original_msg = record.getMessage()
        original_args = record.args
        original_module = record.module
        original_funcName = record.funcName
        original_lineno = record.lineno

        record.levelname = f"{log_color}{original_levelname}{self._RESET}"
        record.msg = f"{log_color}{original_msg}{self._RESET}"
        record.args = None
        record.module = f"{debug_color}{original_module}{self._RESET}"
        record.funcName = f"{debug_color}{original_funcName}{self._RESET}"
        record.lineno = f"{debug_color}{original_lineno}{self._RESET}"

        formatted = super().format(record)

        record.levelname = original_levelname
        record.msg = original_msg
        record.args = original_args
        record.module = original_module
        record.funcName = original_funcName
        record.lineno = original_lineno

        return formatted


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "name": record.name,
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
            "message": record.getMessage(),
        }
        return json.dumps(log_record, ensure_ascii=False, default=str)


def get_logger(
    name: str,
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | None = None,
    format: Literal["console", "json"] | None = None,
) -> logging.Logger:
    if log_level is None:
        log_level = settings.logging.log_level
    if format is None:
        format = settings.logging.format
    if format == "console":
        formatter = ConsoleFormatter(datefmt=DATE_FORMAT)
    elif format == "json":
        formatter = JsonFormatter(datefmt=DATE_FORMAT)
    else:
        raise ValueError(f"Invalid format: {format}")

    logger = logging.getLogger(name)
    logger.setLevel(level=getattr(logging, log_level.upper(), logging.INFO))
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
