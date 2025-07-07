from pathlib import Path
import tempfile
import os
from contextlib import contextmanager

@contextmanager
def temp_path(suffix: str = ""):
    fd, path_str = tempfile.mkstemp(suffix=suffix)
    os.close(fd)  # Close file descriptor immediately to avoid Windows lock
    path = Path(path_str)
    try:
        yield path
    finally:
        if path.exists():
            path.unlink()
