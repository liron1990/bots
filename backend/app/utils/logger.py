# logger_config.py
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
import sys
import pytz
from datetime import datetime


class IsraelTzFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, pytz.timezone("Asia/Jerusalem"))
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Always add a StreamHandler to stdout by default
if not logger.handlers:
    stream_handler = logging.StreamHandler(sys.stdout)
    formatter = IsraelTzFormatter(
        "[%(asctime)s] [%(levelname)s] [%(threadName)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

def setup_logger(logger_name: str, log_dir: Path, level=logging.INFO):
    """
    Set up logging for the root logger (not per-module).
    Adds two TimedRotatingFileHandlers with Israel time formatting:
    - One for INFO and above (logger_name.info.log)
    - One for DEBUG and above (logger_name.debug.log), only if level==DEBUG
    If a previous TimedRotatingFileHandler exists, it is closed and replaced.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)

    # Remove and close any existing TimedRotatingFileHandler
    for handler in list(root_logger.handlers):
        if isinstance(handler, TimedRotatingFileHandler):
            root_logger.removeHandler(handler)
            handler.close()

    # INFO and above handler
    info_log_file = log_dir_path / f"{logger_name}.info.log"
    info_handler = TimedRotatingFileHandler(
        str(info_log_file), when="midnight", backupCount=7, encoding="utf-8"
    )
    info_handler.setLevel(logging.INFO)
    formatter = IsraelTzFormatter(
        "[%(asctime)s] [%(levelname)s] [%(threadName)s] %(name)s: %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    info_handler.setFormatter(formatter)
    root_logger.addHandler(info_handler)

    # DEBUG and above handler (only if level is DEBUG)
    if level <= logging.DEBUG:
        debug_log_file = log_dir_path / f"{logger_name}.debug.log"
        debug_handler = TimedRotatingFileHandler(
            str(debug_log_file), when="midnight", backupCount=7, encoding="utf-8"
        )
        debug_handler.setLevel(logging.DEBUG)
        debug_handler.setFormatter(formatter)
        root_logger.addHandler(debug_handler)
