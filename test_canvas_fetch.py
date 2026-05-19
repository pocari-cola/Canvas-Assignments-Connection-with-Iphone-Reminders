import argparse
import json
import os
import sys
from datetime import datetime, timezone

import requests

import json
import os
import sys

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def get_next_link(link_header):
    if not link_header:
        return None
    parts = link_header.split(",")
    for part in parts:
        section = [item.strip() for item in part.split(";")]
        if len(section) < 2:
            continue
        url_part = section[0]
        rel_part = ";".join(section[1:])
        if "rel=\"next\"" in rel_part:
            if url_part.startswith("<") and url_part.endswith(">"):
                return url_part[1:-1]
    return None


def get_paginated(session, url, params, timeout):
    items = []
    next_url = url
    next_params = params
    while next_url:
        response = session.get(next_url, params=next_params, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list):
            items.extend(data)
        elif isinstance(data, dict) and "items" in data:
            items.extend(data.get("items", []))
        next_url = get_next_link(response.headers.get("Link"))
        next_params = None
    return items


def fetch_courses(session, base_url, timeout):
    url = f"{base_url}/api/v1/courses"
    params = {"enrollment_state": "active", "per_page": 100}
    return get_paginated(session, url, params, timeout)


def main():
    if not os.path.exists(DEFAULT_CONFIG_PATH):
        print("Missing config.json. Copy config.example.json to config.json and fill it.")
        return 1

    config = load_json(DEFAULT_CONFIG_PATH)
    base_url = str(config.get("canvas_base_url", "")).rstrip("/")
    token = str(config.get("canvas_token", "")).strip()
    timeout = int(config.get("request_timeout_seconds", 20))

    if not base_url or not token or "PASTE_" in token:
        print("Canvas token missing in config.json.")
        return 1

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    try:
        courses = fetch_courses(session, base_url, timeout)
    except requests.RequestException as exc:
        print(f"Failed to fetch courses: {exc}")
        return 1

    if not courses:
        print("No courses found.")
        return 0

    for course in courses:
        course_name = str(course.get("name", "")).strip()
        if course_name:
            print(course_name)

    return 0


if __name__ == "__main__":
    sys.exit(main())
    "--only-with-due",
