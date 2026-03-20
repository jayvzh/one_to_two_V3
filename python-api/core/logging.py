"""Unified logging configuration module.

This module provides centralized logging setup for the entire application.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime
from typing import Any

CONSOLE_LOG_FORMAT = "%(asctime)s | %(levelname)-7s | %(short_name)-18s | %(message)s"
FILE_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-7s | %(name)s | %(filename)s:%(lineno)d | %(message)s"
)
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

LOG_LEVEL_DEBUG = logging.DEBUG
LOG_LEVEL_INFO = logging.INFO
LOG_LEVEL_WARNING = logging.WARNING
LOG_LEVEL_ERROR = logging.ERROR
LOG_LEVEL_CRITICAL = logging.CRITICAL

_logger_cache: dict[str, logging.Logger] = {}
_root_configured = False

_LEVEL_COLOR = {
    "DEBUG": "\x1b[36m",
    "INFO": "\x1b[32m",
    "WARNING": "\x1b[33m",
    "ERROR": "\x1b[31m",
    "CRITICAL": "\x1b[35m",
}
_COLOR_RESET = "\x1b[0m"


class _ShortModuleFilter(logging.Filter):
    """Attach a shortened module name for readable aligned output."""

    def filter(self, record: logging.LogRecord) -> bool:
        name = record.name or "root"
        if name == "__main__":
            short_name = "main"
        else:
            short_name = name.split(".")[-2:] if "." in name else [name]
            short_name = ".".join(short_name)
        record.short_name = short_name
        return True


class _ColorFormatter(logging.Formatter):
    """Apply ANSI color to level name for console readability."""

    def __init__(self, fmt: str, datefmt: str, use_color: bool = True):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        original = record.levelname
        if self.use_color:
            color = _LEVEL_COLOR.get(original)
            if color:
                record.levelname = f"{color}{original}{_COLOR_RESET}"
        try:
            return super().format(record)
        finally:
            record.levelname = original


class _JsonFormatter(logging.Formatter):
    """Emit logs as JSON lines for machine processing."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created).strftime(DATE_FORMAT),
            "level": record.levelname,
            "logger": record.name,
            "short_logger": getattr(record, "short_name", record.name),
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class _TqdmCompatibleHandler(logging.StreamHandler):
    """Keep progress bars intact by routing logs through tqdm when available."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            try:
                from tqdm import tqdm

                tqdm.write(msg, file=self.stream)
                self.flush()
            except Exception:
                self.stream.write(msg + self.terminator)
                self.flush()
        except Exception:
            self.handleError(record)


def setup_logging(
    level: int = logging.INFO,
    log_file: str | None = None,
    json_log_file: str | None = None,
    use_color: bool = True,
) -> None:
    """Setup unified logging configuration.

    Args:
        level: Logging level (default: logging.INFO).
        log_file: Optional path to plain-text detailed log file.
        json_log_file: Optional path to JSON-lines log file.
        use_color: Whether to color console log levels.
    """
    global _root_configured

    root_logger = logging.getLogger()

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.setLevel(level)

    short_name_filter = _ShortModuleFilter()

    enable_color = use_color and sys.stdout.isatty() and os.getenv("NO_COLOR") is None
    console_formatter = _ColorFormatter(CONSOLE_LOG_FORMAT, datefmt=DATE_FORMAT, use_color=enable_color)

    console_handler = _TqdmCompatibleHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(short_name_filter)
    root_logger.addHandler(console_handler)

    if log_file:
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter(FILE_LOG_FORMAT, datefmt=DATE_FORMAT))
        file_handler.addFilter(short_name_filter)
        root_logger.addHandler(file_handler)

    if json_log_file:
        json_handler = logging.FileHandler(json_log_file, encoding="utf-8")
        json_handler.setLevel(level)
        json_handler.setFormatter(_JsonFormatter())
        json_handler.addFilter(short_name_filter)
        root_logger.addHandler(json_handler)

    _root_configured = True


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    global _root_configured

    if not _root_configured:
        setup_logging()

    if name in _logger_cache:
        return _logger_cache[name]

    logger = logging.getLogger(name)
    _logger_cache[name] = logger

    return logger


def log_banner(logger: logging.Logger, title: str, width: int = 50, char: str = "=") -> None:
    """Log a section banner in consistent style."""
    logger.info(char * width)
    logger.info(title)
    logger.info(char * width)


def log_stage(logger: logging.Logger, stage: int, total: int, title: str, width: int = 50) -> None:
    """Log a pipeline stage with divider."""
    logger.info(f"[阶段 {stage}/{total}] {title}")
    logger.info("-" * width)


def log_metrics(logger: logging.Logger, title: str | None = None, **metrics: Any) -> None:
    """Log key metrics as compact key=value items in a single line."""
    if title:
        prefix = f"{title}: "
    else:
        prefix = ""

    parts = []
    for key, value in metrics.items():
        if isinstance(value, float):
            if abs(value) <= 1:
                parts.append(f"{key}={value:.2%}")
            else:
                parts.append(f"{key}={value:.4f}")
        else:
            parts.append(f"{key}={value}")

    logger.info(prefix + " | ".join(parts))
