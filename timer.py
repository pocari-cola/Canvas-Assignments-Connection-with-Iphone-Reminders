import json
import os
import subprocess
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "timercfg.json")
TARGET_SCRIPT = os.path.join(SCRIPT_DIR, "canvas_pushcut.py")


def load_config():
    if not os.path.exists(CONFIG_PATH):
        print("Missing timercfg.json. Create it and set interval_seconds.")
        return None
    with open(CONFIG_PATH, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def now_stamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def run_once():
    print(f"[{now_stamp()}] Running canvas_pushcut.py")
    result = subprocess.run([sys.executable, TARGET_SCRIPT], check=False)
    print(f"[{now_stamp()}] Exit code: {result.returncode}")
    return result.returncode


def main():
    config = load_config()
    if config is None:
        return 1

    interval_hours = float(config.get("interval_hours", 3))
    run_immediately = bool(config.get("run_immediately", True))
    stop_on_error = bool(config.get("stop_on_error", False))

    if interval_hours <= 0:
        print("interval_hours must be a positive number.")
        return 1
    if not os.path.exists(TARGET_SCRIPT):
        print("Missing canvas_pushcut.py.")
        return 1

    if run_immediately:
        exit_code = run_once()
        if exit_code != 0 and stop_on_error:
            return exit_code

    interval_seconds = interval_hours * 3600
    while True:
        next_run = time.time() + interval_seconds
        next_time = datetime.fromtimestamp(next_run).strftime("%Y-%m-%d %H:%M:%S")
        print(f"Next run at {next_time}")
        time.sleep(interval_seconds)
        exit_code = run_once()
        if exit_code != 0 and stop_on_error:
            return exit_code


if __name__ == "__main__":
    sys.exit(main())
