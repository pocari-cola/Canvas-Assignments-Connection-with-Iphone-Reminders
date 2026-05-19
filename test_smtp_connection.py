import argparse
import json
import os
import sys
import smtplib
from email.message import EmailMessage

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")


def load_json(path):
    with open(path, "r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def build_message(from_addr, to_addr):
    message = EmailMessage()
    message["From"] = from_addr
    message["To"] = to_addr
    message["Subject"] = "SMTP connection test"
    message.set_content("This is a test email from the Canvas SMTP checker.")
    return message


def main():
    parser = argparse.ArgumentParser(description="Test SMTP login and optional send")
    parser.add_argument(
        "--send",
        action="store_true",
        help="Send a test email after login",
    )
    args = parser.parse_args()

    if not os.path.exists(DEFAULT_CONFIG_PATH):
        print("Missing config.json. Copy config.example.json to config.json and fill it.")
        return 1

    config = load_json(DEFAULT_CONFIG_PATH)
    smtp_host = str(config.get("smtp_host", "")).strip()
    smtp_port = int(config.get("smtp_port", 587))
    smtp_username = str(config.get("smtp_username", "")).strip()
    smtp_password = str(config.get("smtp_password", "")).strip()
    smtp_from = str(config.get("smtp_from", "")).strip() or smtp_username
    smtp_to = str(config.get("smtp_to", "")).strip() or smtp_username
    smtp_use_tls = bool(config.get("smtp_use_tls", True))
    smtp_use_ssl = bool(config.get("smtp_use_ssl", False))
    timeout = int(config.get("smtp_timeout_seconds", 20))

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

    server = None
    try:
        if smtp_use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=timeout)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=timeout)
            server.ehlo()
            if smtp_use_tls:
                server.starttls()
                server.ehlo()

        server.login(smtp_username, smtp_password)
        print("SMTP login successful.")

        if args.send:
            message = build_message(smtp_from, smtp_to)
            server.send_message(message)
            print("Test email sent.")
        else:
            print("No email sent (use --send to send a test message).")
    except (smtplib.SMTPException, OSError) as exc:
        print(f"SMTP test failed: {exc}")
        return 1
    finally:
        if server is not None:
            try:
                server.quit()
            except (smtplib.SMTPException, OSError):
                pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
