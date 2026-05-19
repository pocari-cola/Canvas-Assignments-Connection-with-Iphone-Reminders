import json
import os
import smtplib
import sys
from datetime import datetime, timezone
from email.message import EmailMessage

import requests

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")
ASSIGNMENT_DUMP_PATH = os.path.join(SCRIPT_DIR, "assignment.json")
COURSE_ALIAS_PATH = os.path.join(SCRIPT_DIR, "course_aliases.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, ensure_ascii=True, indent=2)
        file_handle.write("\n")


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


def should_include_assignment(assignment, include_past_due):
    if not assignment.get("published", True):
        return False
    due_at = parse_iso_datetime(assignment.get("due_at"))
    if due_at is None:
        return False
    if not include_past_due:
        now_utc = datetime.now(timezone.utc)
        if due_at.astimezone(timezone.utc) < now_utc:
            return False
    return True


def build_email_payload(assignment, course_label):
    return {
        "course_name": course_label,
        "assignment_name": assignment.get("name", ""),
        "due_at": assignment.get("due_at"),
    }


def build_email_subject(subject_prefix, payload):
    prefix = subject_prefix.strip() or "CanvasAssignment"
    title = " - ".join(
        part
        for part in [payload.get("course_name", ""), payload.get("assignment_name", "")]
        if part
    )
    if title:
        return f"{prefix} {title}"
    return prefix


def build_assignment_record(assignment, course_id, course_name, course_alias):
    return {
        "course_id": course_id,
        "course_name": course_name,
        "course_alias": course_alias,
        "assignment": assignment,
    }


def load_course_aliases(path):
    if not os.path.exists(path):
        print("Missing course_aliases.json. Create it to map course names to short labels.")
        return None
    data = load_json(path)
    if not isinstance(data, dict):
        print("course_aliases.json must be a JSON object mapping course names to short labels.")
        return None
    aliases = {}
    for key, value in data.items():
        key_str = str(key).strip()
        value_str = str(value).strip()
        if key_str and value_str:
            aliases[key_str] = value_str
    return aliases


def send_email(
    host,
    port,
    username,
    password,
    from_addr,
    to_addr,
    subject,
    body,
    use_tls,
    use_ssl,
    timeout,
):
    message = EmailMessage()
    message["From"] = from_addr
    message["To"] = to_addr
    message["Subject"] = subject
    message.set_content(body)

    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=timeout) as server:
            server.login(username, password)
            server.send_message(message)
        return

    with smtplib.SMTP(host, port, timeout=timeout) as server:
        server.ehlo()
        if use_tls:
            server.starttls()
            server.ehlo()
        server.login(username, password)
        server.send_message(message)


def load_state(path):
    if not os.path.exists(path):
        return {"initialized": False, "seen_assignment_ids": []}
    return load_json(path)


def main():
    if not os.path.exists(DEFAULT_CONFIG_PATH):
        print("Missing config.json. Copy config.example.json to config.json and fill it.")
        return 1

    config = load_json(DEFAULT_CONFIG_PATH)
    base_url = str(config.get("canvas_base_url", "")).rstrip("/")
    token = str(config.get("canvas_token", "")).strip()
    smtp_host = str(config.get("smtp_host", "")).strip()
    smtp_port = int(config.get("smtp_port", 587))
    smtp_username = str(config.get("smtp_username", "")).strip()
    smtp_password = str(config.get("smtp_password", "")).strip()
    smtp_from = str(config.get("smtp_from", "")).strip()
    smtp_to = str(config.get("smtp_to", "")).strip()
    smtp_use_tls = bool(config.get("smtp_use_tls", True))
    smtp_use_ssl = bool(config.get("smtp_use_ssl", False))
    smtp_subject_prefix = str(config.get("smtp_subject_prefix", "CanvasAssignment")).strip()
    initial_sync_only = bool(config.get("initial_sync_only", True))
    include_past_due = bool(config.get("include_past_due", False))
    state_file = str(config.get("state_file", "state.json")).strip()
    timeout = int(config.get("request_timeout_seconds", 20))
    smtp_timeout = int(config.get("smtp_timeout_seconds", timeout))

    if not base_url or not token or "PASTE_" in token:
        print("Canvas token missing in config.json.")
        return 1
    if not smtp_host:
        print("SMTP host missing in config.json.")
        return 1
    if not smtp_port:
        print("SMTP port missing in config.json.")
        return 1
    if not smtp_username or "PASTE_" in smtp_username:
        print("SMTP username missing in config.json.")
        return 1
    if not smtp_password or "PASTE_" in smtp_password:
        print("SMTP password missing in config.json.")
        return 1
    if smtp_use_ssl and smtp_use_tls:
        print("Configure SMTP to use SSL or TLS, not both.")
        return 1
    if not smtp_from:
        smtp_from = smtp_username
    if not smtp_to:
        smtp_to = smtp_username

    course_aliases = load_course_aliases(COURSE_ALIAS_PATH)
    if course_aliases is None:
        return 1
    if not course_aliases:
        print("course_aliases.json is empty. No emails will be sent until you add mappings.")

    state_path = os.path.join(SCRIPT_DIR, state_file)
    state = load_state(state_path)
    seen = set(str(value) for value in state.get("seen_assignment_ids", []))

    canvas_session = requests.Session()
    canvas_session.headers.update({"Authorization": f"Bearer {token}"})

    try:
        courses = fetch_courses(canvas_session, base_url, timeout)
    except requests.RequestException as exc:
        print(f"Failed to fetch courses: {exc}")
        return 1

    assignments_to_check = []
    all_assignments = []
    for course in courses:
        course_id = course.get("id")
        course_name = course.get("name", f"Course {course_id}")
        course_alias = course_aliases.get(course_name)
        if not course_id:
            continue
        try:
            assignments = fetch_assignments(canvas_session, base_url, course_id, timeout)
        except requests.RequestException as exc:
            print(f"Failed to fetch assignments for course {course_id}: {exc}")
            continue
        for assignment in assignments:
            all_assignments.append(
                build_assignment_record(assignment, course_id, course_name, course_alias)
            )
            if not should_include_assignment(assignment, include_past_due):
                continue
            if not course_alias:
                continue
            assignments_to_check.append((assignment, course_alias))

    assignment_dump = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "course_count": len(courses),
        "assignment_count": len(all_assignments),
        "assignments": all_assignments,
    }
    save_json(ASSIGNMENT_DUMP_PATH, assignment_dump)

    if not state.get("initialized", False) and initial_sync_only:
        for assignment, _ in assignments_to_check:
            assignment_id = assignment.get("id")
            if assignment_id is not None:
                seen.add(str(assignment_id))
        state["seen_assignment_ids"] = sorted(seen)
        state["initialized"] = True
        save_json(state_path, state)
        print("Initial sync complete. No emails sent.")
        return 0

    new_count = 0
    for assignment, course_name in assignments_to_check:
        assignment_id = assignment.get("id")
        if assignment_id is None:
            continue
        assignment_id_str = str(assignment_id)
        if assignment_id_str in seen:
            continue
        payload = build_email_payload(assignment, course_name)
        subject = build_email_subject(smtp_subject_prefix, payload)
        body = json.dumps(payload, ensure_ascii=True)
        try:
            send_email(
                smtp_host,
                smtp_port,
                smtp_username,
                smtp_password,
                smtp_from,
                smtp_to,
                subject,
                body,
                smtp_use_tls,
                smtp_use_ssl,
                smtp_timeout,
            )
        except (smtplib.SMTPException, OSError) as exc:
            print(f"Failed to send email for assignment {assignment_id_str}: {exc}")
            continue
        seen.add(assignment_id_str)
        state["seen_assignment_ids"] = sorted(seen)
        state["initialized"] = True
        save_json(state_path, state)
        new_count += 1

    print(f"Done. New emails sent: {new_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
