import argparse
import json
import os
import sys
from datetime import datetime, timezone

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def parse_iso_datetime(value):
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def format_local_datetime(value):
    if value is None:
        return ""
    return value.astimezone().strftime("%Y-%m-%d %H:%M")


def get_next_link(link_header):
    if not link_header:
        return None
    parts = link_header.split(",")
    for part in parts:
        section = [item.strip() for item in part.split("; ")]
        if len(section) < 2:
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


def fetch_assignments(session, base_url, course_id, timeout):
    url = f"{base_url}/api/v1/courses/{course_id}/assignments"
    params = {"per_page": 100, "order_by": "due_at"}
    return get_paginated(session, url, params, timeout)


def main():
    parser = argparse.ArgumentParser(description="Fetch Canvas assignments for validation")
    parser.add_argument("--course-id", type=int, default=None, help="Only fetch a single course ID")
    parser.add_argument("--limit", type=int, default=30, help="Max assignments to print")
    parser.add_argument(
        "--include-past-due",
        action="store_true",
        help="Include assignments whose due date already passed",
    )
    parser.add_argument(
        "--show-unpublished",
        action="store_true",
        help="Include unpublished assignments",
    )
    parser.add_argument(
        "--only-with-due",
        action="store_true",
        help="Only show assignments that have due_at",
    )
    args = parser.parse_args()

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

    if args.course_id is not None:
        courses = [course for course in courses if course.get("id") == args.course_id]
        if not courses:
            print(f"No matching course for ID {args.course_id}")
            return 1

    printed = 0
    total_seen = 0
    now_utc = datetime.now(timezone.utc)

    for course in courses:
        course_id = course.get("id")
        course_name = course.get("name", f"Course {course_id}")
        if not course_id:
            continue
        try:
            assignments = fetch_assignments(session, base_url, course_id, timeout)
        except requests.RequestException as exc:
            print(f"Failed to fetch assignments for course {course_id}: {exc}")
            continue

        for assignment in assignments:
            total_seen += 1
            if not args.show_unpublished and not assignment.get("published", True):
                continue

            due_at = parse_iso_datetime(assignment.get("due_at"))
            if args.only_with_due and due_at is None:
                continue
            if not args.include_past_due and due_at is not None:
                if due_at.astimezone(timezone.utc) < now_utc:
                    continue

            due_local = format_local_datetime(due_at)
            print(
                f"[{course_name}] id={assignment.get('id')} name={assignment.get('name', '')} "
                f"due_at={assignment.get('due_at', '')} due_local={due_local}"
            )
            printed += 1
            if args.limit and printed >= args.limit:
                print(f"Reached limit {args.limit}.")
                print(f"Total assignments scanned: {total_seen}")
                return 0

    print(f"Done. Printed {printed} assignments. Total scanned: {total_seen}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
