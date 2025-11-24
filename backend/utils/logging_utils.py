import logging
import sys
from pathlib import Path
from typing import Optional


def get_job_log_path(name: str, log_file: Optional[str] = None) -> Path:
    """
    Return the absolute path to the log file for a given job logger.
    """
    logs_dir = Path(__file__).resolve().parent.parent / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    file_name = log_file or f"{name}.log"
    return logs_dir / file_name


def get_job_logger(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """
    Return a logger configured to write both to stdout and to a dedicated log file.

    Ensures idempotent configuration so multiple imports do not add duplicate handlers.

    Args:
        name: Logical name of the logger (used as logging namespace and default file name).
        log_file: Optional explicit log file name. Defaults to `<name>.log`.
    """
    logger = logging.getLogger(name)

    if getattr(logger, "_job_logger_configured", False):
        return logger

    logger.setLevel(logging.INFO)

    log_path = get_job_log_path(name, log_file)

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    # Create a custom handler that flushes after each write for immediate file updates
    class FlushingFileHandler(logging.FileHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()
    
    # Use flushing file handler for immediate writes
    file_handler = FlushingFileHandler(log_path, encoding="utf-8", mode='a')
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    logger._job_logger_configured = True  # type: ignore[attr-defined]

    return logger

