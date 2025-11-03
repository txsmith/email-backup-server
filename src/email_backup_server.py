#!/usr/bin/env python3
"""
Minimal SMTP Server for Email Backup
Receives emails and stores them in Maildir format
"""

import asyncio
import email
import os
from datetime import datetime
from pathlib import Path
from aiosmtpd.controller import Controller
import mailbox
import spf


class EmailBackupHandler:
    """Handler that receives emails and stores them in Maildir format"""

    def __init__(
        self,
        maildir_path,
        allowed_recipient=None,
        allowed_sender_domains=None,
        require_spf_pass=False,
        required_headers=None,
    ):
        self.maildir_path = Path(maildir_path)
        # Ensure the maildir path and subdirectories exist
        self.maildir_path.mkdir(parents=True, exist_ok=True)
        for subdir in ["tmp", "new", "cur"]:
            (self.maildir_path / subdir).mkdir(exist_ok=True)
        self.maildir = mailbox.Maildir(self.maildir_path, create=True)
        self.allowed_recipient = allowed_recipient.lower() if allowed_recipient else None
        self.allowed_sender_domains = (
            [d.lower() for d in allowed_sender_domains] if allowed_sender_domains else []
        )
        self.require_spf_pass = require_spf_pass
        # Store required headers as dict of {header_name: expected_value}
        self.required_headers = {}
        if required_headers:
            for header_pair in required_headers:
                if ":" in header_pair:
                    header, value = header_pair.split(":", 1)
                    self.required_headers[header.strip().lower()] = value.strip().lower()

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """Validate recipient address before accepting"""
        if self.allowed_recipient:
            if address.lower() != self.allowed_recipient:
                print(f"Rejected to {address}: wrong recipient")
                return "550 Recipient not accepted"

        # Accept the recipient
        envelope.rcpt_tos.append(address)
        return "250 OK"

    def _validate_sender_domain(self, envelope):
        """Validate sender domain against whitelist"""
        if not self.allowed_sender_domains:
            return None

        sender_domain = envelope.mail_from.split("@")[-1].lower()
        if sender_domain not in self.allowed_sender_domains:
            print(f"Rejected from {envelope.mail_from}: unauthorized domain {sender_domain}")
            return "550 Sender domain not authorized"
        return None

    def _validate_spf(self, session, envelope):
        """Validate SPF record for sender"""
        if not self.require_spf_pass:
            return None

        client_ip = session.peer[0]
        helo_name = session.host_name if hasattr(session, "host_name") else "unknown"

        try:
            result, explanation = spf.check2(i=client_ip, s=envelope.mail_from, h=helo_name)

            if result not in ["pass", "none"]:
                print(f"Rejected from {envelope.mail_from}: SPF {result} (IP: {client_ip})")
                return f"550 SPF validation failed: {result}"

            if result == "pass":
                print(f"SPF pass: {envelope.mail_from} from {client_ip}")
        except Exception as e:
            print(f"Rejected from {envelope.mail_from}: SPF error ({e})")
            return "451 SPF validation error"

        return None

    def _validate_required_headers(self, msg):
        """Validate required email headers"""
        if not self.required_headers:
            return None

        for required_header, required_value in self.required_headers.items():
            header_value = msg.get(required_header, "")
            if header_value.lower() != required_value:
                from_addr = msg.get("From", "unknown")
                subject = msg.get("Subject", "(no subject)")
                print(f"Rejected from {from_addr}: {subject} (header mismatch)")
                return "550 Message rejected"
        return None

    async def handle_DATA(self, server, session, envelope):
        """Called when an email is received"""
        # Validate sender domain
        error = self._validate_sender_domain(envelope)
        if error:
            return error

        # Validate SPF
        error = self._validate_spf(session, envelope)
        if error:
            return error

        # Parse email message
        msg = email.message_from_bytes(envelope.content)

        # Validate required headers
        error = self._validate_required_headers(msg)
        if error:
            return error

        msg["X-Backup-Received"] = datetime.now().isoformat()
        msg["X-Backup-From"] = envelope.mail_from
        msg["X-Backup-To"] = ", ".join(envelope.rcpt_tos)

        self.maildir.add(msg)

        subject = msg.get("Subject", "(no subject)")
        from_addr = msg.get("From", envelope.mail_from)

        print(f"Received from {from_addr}: {subject} ({len(envelope.content)} bytes)")

        return "250 Message accepted for delivery"


class EmailBackupServer:
    """SMTP server wrapper"""

    def __init__(
        self,
        host="0.0.0.0",
        port=25,
        maildir_path="~/email",
        allowed_recipient=None,
        allowed_sender_domains=None,
        require_spf_pass=False,
        required_headers=None,
    ):
        self.host = host
        self.port = port
        self.maildir_path = os.path.expanduser(maildir_path)
        self.allowed_recipient = allowed_recipient
        self.allowed_sender_domains = allowed_sender_domains
        self.require_spf_pass = require_spf_pass
        self.required_headers = required_headers

        self.handler = EmailBackupHandler(
            self.maildir_path,
            allowed_recipient=allowed_recipient,
            allowed_sender_domains=allowed_sender_domains,
            require_spf_pass=require_spf_pass,
            required_headers=required_headers,
        )

        self.controller = Controller(self.handler, hostname=self.host, port=self.port)

    def start(self):
        """Start the SMTP server"""
        print("=" * 60)
        print("Email Backup SMTP Server")
        print("=" * 60)
        print(f"Host: {self.host}")
        print(f"Port: {self.port}")
        print(f"Storage: {self.maildir_path}")
        if self.allowed_recipient:
            print(f"Allowed Recipient: {self.allowed_recipient}")
        if self.allowed_sender_domains:
            print(f"Allowed Sender Domains: {', '.join(self.allowed_sender_domains)}")
        if self.require_spf_pass:
            print("SPF Validation: ENABLED")
        if self.required_headers:
            print(f"Required Headers: {len(self.required_headers)} filter(s)")
        print("=" * 60)

        self.controller.start()

    def stop(self):
        """Stop the SMTP server"""
        print("Stopping server...")
        self.controller.stop()
        print("Server stopped")


async def async_main():
    """Async main function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Minimal SMTP server for email backup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run on default port 25 (requires root/sudo)
  sudo python3 email_backup_server.py

  # Run on non-privileged port 2525
  python3 email_backup_server.py --port 2525

  # Specify custom storage location
  python3 email_backup_server.py --port 2525 --maildir /path/to/backup

  # Listen on specific interface
  python3 email_backup_server.py --host 192.168.1.100 --port 2525
""",
    )

    parser.add_argument(
        "--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0 - all interfaces)"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=2525,
        help="Port to listen on (default: 2525, use 25 for standard SMTP)",
    )

    parser.add_argument(
        "--maildir",
        default="~/email",
        help="Path to store emails in Maildir format (default: ~/email)",
    )

    parser.add_argument(
        "--allowed-recipient",
        help="Only accept emails to this specific address (e.g., random123@yourdomain.com)",
    )

    parser.add_argument(
        "--allowed-domains",
        nargs="+",
        help="Only accept emails from these sender domains (e.g., hey.com mail.hey.com)",
    )

    parser.add_argument(
        "--disable-spf",
        action="store_true",
        help="Disable SPF validation (not recommended - allows IP spoofing)",
    )

    parser.add_argument(
        "--required-header",
        action="append",
        help='Require specific header value (format: "Header-Name:value"). '
        "Can be specified multiple times.",
    )

    args = parser.parse_args()

    server = EmailBackupServer(
        host=args.host,
        port=args.port,
        maildir_path=args.maildir,
        allowed_recipient=args.allowed_recipient,
        allowed_sender_domains=args.allowed_domains,
        require_spf_pass=not args.disable_spf,
        required_headers=args.required_header,
    )

    try:
        server.start()
        await asyncio.Event().wait()  # Wait forever
    except KeyboardInterrupt:
        server.stop()


def main():
    """Entry point that runs the async main function."""
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
