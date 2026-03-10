"""
Pipeline logging utility.
Appends timestamped entries to logs/pipeline.log.

CLI usage:
    python scripts/log.py INFO "Phase 1 started"
    python scripts/log.py RUN "Pipeline started"

Importable:
    from log import pipeline_log
"""

import sys
import os
from datetime import datetime, timezone

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_FILE = os.path.join(LOG_DIR, "pipeline.log")

VALID_LEVELS = {"RUN", "INFO", "DETAIL", "WARN", "ERROR"}


def pipeline_log(level: str, message: str) -> None:
    """Append a timestamped log entry to the pipeline log file."""
    level = level.upper()
    if level not in VALID_LEVELS:
        level = "INFO"

    os.makedirs(LOG_DIR, exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    if level == "RUN" and message.lower().startswith("pipeline started"):
        line = f"\n===== RUN START {now} =====\n"
    elif level == "RUN" and message.lower().startswith("pipeline complete"):
        line = f"[{now}] [RUN] {message}\n===== RUN END =====\n"
    else:
        line = f"[{now}] [{level}] {message}\n"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python scripts/log.py LEVEL \"message\"")
        print("Levels: RUN, INFO, DETAIL, WARN, ERROR")
        sys.exit(1)

    level = sys.argv[1]
    message = " ".join(sys.argv[2:])
    pipeline_log(level, message)
