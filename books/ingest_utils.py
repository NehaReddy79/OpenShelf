import logging
import os
import time
from datetime import datetime , timezone

logger = logging.getLogger(__name__)

def parse_ts(value):
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def read_checkpoint(path):
    try:
        with open(path) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return 0


def write_checkpoint(path, line_number , retries = 5 , base_delay = 0.1):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(str(line_number))

    for attempt in range(retries):
        try:
            os.replace(tmp, path)
            return True
        except PermissionError:
            if attempt < retries - 1:
                time.sleep(base_delay * (2 ** attempt))

    logger.warning(
        "Could not update checkpoint at line %s after %s attempts. Continuing.",
        line_number, retries,
    )
    try : 
        os.remove(tmp)
    except OSError : 
        pass
    return False
    