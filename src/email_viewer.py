#!/usr/bin/env python3
"""
Simple Email Viewer for Maildir
Browse and search your backed-up emails
"""

import mailbox
import argparse
import sys
import os
from email.utils import parsedate_to_datetime


def format_date(date_str):
    """Format email date string"""
    if not date_str:
        return "Unknown date"

    try:
        dt = parsedate_to_datetime(date_str)
        return dt.strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return "Unknown date"


def get_body(message):
    """Extract text body from email message"""
    body = ""

    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                    break
                except (AttributeError, UnicodeDecodeError):
                    continue
    else:
        try:
            body = message.get_payload(decode=True).decode("utf-8", errors="ignore")
        except (AttributeError, UnicodeDecodeError):
            body = message.get_payload()

    return body


def list_emails(maildir_path, limit=20, search=None):
    """List emails in the maildir"""
    md = mailbox.Maildir(maildir_path)

    emails = []

    for key, message in md.items():
        # Extract info
        from_addr = message.get("From", "Unknown")
        subject = message.get("Subject", "(no subject)")
        date = format_date(message.get("Date"))

        # Apply search filter if provided
        if search:
            search_lower = search.lower()
            searchable_text = f"{from_addr} {subject}".lower()
            body = get_body(message)
            searchable_text += f" {body}".lower()

            if search_lower not in searchable_text:
                continue

        emails.append(
            {"key": key, "from": from_addr, "subject": subject, "date": date, "message": message}
        )

    # Sort by date (newest first)
    emails.sort(key=lambda x: x["date"], reverse=True)

    # Limit results
    emails = emails[:limit]

    if not emails:
        print("No emails found.")
        return

    # Display results
    print(f"\n{'#':<4} {'Date':<17} {'From':<30} {'Subject':<50}")
    print("=" * 110)

    for idx, email in enumerate(emails, 1):
        from_addr = email["from"][:28] + ".." if len(email["from"]) > 30 else email["from"]
        subject = email["subject"][:48] + ".." if len(email["subject"]) > 50 else email["subject"]
        print(f"{idx:<4} {email['date']:<17} {from_addr:<30} {subject:<50}")

    print()
    return emails


def view_email(maildir_path, email_id):
    """View a specific email by ID"""
    md = mailbox.Maildir(maildir_path)
    message = md[email_id]

    print("\n" + "=" * 80)
    print(f"From:    {message.get('From', 'Unknown')}")
    print(f"To:      {message.get('To', 'Unknown')}")
    print(f"Date:    {format_date(message.get('Date'))}")
    print(f"Subject: {message.get('Subject', '(no subject)')}")
    print("=" * 80)
    print()

    body = get_body(message)
    print(body)
    print()


def interactive_mode(maildir_path):
    """Interactive email browser"""
    print("Email Viewer - Interactive Mode")
    print("=" * 50)
    print()

    current_emails = None

    while True:
        print("\nCommands:")
        print("  list [N]      - List up to N emails (default: 20)")
        print("  search TEXT   - Search emails for TEXT")
        print("  view N        - View email number N from last listing")
        print("  quit          - Exit")
        print()

        try:
            cmd = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not cmd:
            continue

        parts = cmd.split(maxsplit=1)
        command = parts[0].lower()

        if command in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        elif command == "list":
            limit = 20
            if len(parts) > 1:
                try:
                    limit = int(parts[1])
                except ValueError:
                    print("Invalid number")
                    continue
            current_emails = list_emails(maildir_path, limit=limit)

        elif command == "search":
            if len(parts) < 2:
                print("Please provide search text")
                continue
            current_emails = list_emails(maildir_path, limit=50, search=parts[1])

        elif command == "view":
            if not current_emails:
                print("Please list emails first")
                continue
            if len(parts) < 2:
                print("Please provide email number")
                continue
            try:
                idx = int(parts[1]) - 1
                if 0 <= idx < len(current_emails):
                    view_email(maildir_path, current_emails[idx]["key"])
                else:
                    print(f"Invalid email number. Please choose 1-{len(current_emails)}")
            except ValueError:
                print("Invalid number")

        else:
            print(f"Unknown command: {command}")


def main():
    parser = argparse.ArgumentParser(
        description="View and search emails in Maildir format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "maildir",
        nargs="?",
        default="~/email",
        help="Path to maildir (default: ~/email)",
    )

    parser.add_argument("--list", "-l", action="store_true", help="List recent emails and exit")

    parser.add_argument(
        "--limit", "-n", type=int, default=20, help="Number of emails to show (default: 20)"
    )

    parser.add_argument("--search", "-s", help="Search for text in emails")

    args = parser.parse_args()

    maildir_path = os.path.expanduser(args.maildir)

    if not os.path.exists(maildir_path):
        print(f"Error: Maildir not found at {maildir_path}")
        sys.exit(1)

    if args.list or args.search:
        list_emails(maildir_path, limit=args.limit, search=args.search)
    else:
        interactive_mode(maildir_path)


if __name__ == "__main__":
    main()
