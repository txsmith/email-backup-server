#!/usr/bin/env python3
"""
Convert email files (RFC 822 format) to Markdown.

This script parses email files, extracts HTML content, and converts it to Markdown format.
It handles:
- Quoted-printable encoding
- HTML to Markdown conversion
- Email metadata extraction (Subject, From, To, Date)
"""

import email
import sys
from email import policy
from html2text import HTML2Text
from pathlib import Path


def convert_email_to_markdown(email_path: str, output_path: str = None) -> str:
    """
    Convert an email file to Markdown format.

    Args:
        email_path: Path to the email file
        output_path: Optional path to save the markdown file

    Returns:
        Markdown content as a string
    """
    # Read and parse the email
    with open(email_path, "rb") as f:
        msg = email.message_from_binary_file(f, policy=policy.default)

    # Extract metadata
    subject = msg.get("Subject", "No Subject")
    from_addr = msg.get("From", "Unknown")
    to_addr = msg.get("To", "Unknown")
    date = msg.get("Date", "Unknown")

    # Initialize HTML2Text converter
    h = HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0  # Don't wrap lines
    h.unicode_snob = True  # Use unicode characters
    h.ignore_tables = False

    # Extract HTML body
    html_body = None
    text_body = None

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/html":
                html_body = part.get_content()
            elif content_type == "text/plain" and text_body is None:
                text_body = part.get_content()
    else:
        content_type = msg.get_content_type()
        if content_type == "text/html":
            html_body = msg.get_content()
        elif content_type == "text/plain":
            text_body = msg.get_content()

    # Convert to markdown
    markdown_content = f"""---
Subject: {subject}
From: {from_addr}
To: {to_addr}
Date: {date}
---

"""

    if html_body:
        # Convert HTML to Markdown
        markdown_body = h.handle(html_body)
        markdown_content += markdown_body
    elif text_body:
        # Use plain text if no HTML
        markdown_content += text_body
    else:
        markdown_content += "*No content found in email*\n"

    # Save to file if output path is provided
    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"Markdown saved to: {output_path}")

    return markdown_content


def main():
    if len(sys.argv) < 2:
        print("Usage: python email_to_markdown.py <email_file> [output_file]")
        print("\nExample:")
        print("  python email_to_markdown.py email.eml output.md")
        print("  python email_to_markdown.py email.eml  # prints to stdout")
        sys.exit(1)

    email_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None

    if not Path(email_path).exists():
        print(f"Error: Email file not found: {email_path}")
        sys.exit(1)

    try:
        markdown = convert_email_to_markdown(email_path, output_path)

        # Print to stdout if no output file specified
        if not output_path:
            print(markdown)

    except Exception as e:
        print(f"Error converting email: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
