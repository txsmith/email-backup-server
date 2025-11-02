# Email Backup SMTP Server

A minimal SMTP server that receives forwarded emails and stores them locally in Maildir format for backup and archival.

## Running the Server

```bash
# Install and run
uv run email-backup-server \
  --host 0.0.0.0 \
  --port 2525 \
  --maildir ~/email \
  --allowed-recipient backup-7a3f9e2b4c1d8f6a@yourdomain.com \
  --allowed-domains example.com \
  --required-header "X-Original-To:me@example.com"
```

**Options:**
- `--host`: Interface to bind to (default: 0.0.0.0)
- `--port`: Port to listen on (default: 2525, use 25 for standard SMTP)
- `--maildir`: Path to store emails (default: ~/email)
- `--allowed-recipient`: Only accept emails to this specific address
- `--allowed-domains`: Only accept emails from these sender domains (space-separated)
- `--required-header`: Require specific header value (format: "Header:value"). Can be specified multiple times
- `--disable-spf`: Disable SPF validation (enabled by default)

## Running with Docker

```bash
docker run -d \
  --name email-backup \
  -p 2525:2525 \
  -v /path/to/email:/data/email \
  -e SMTP_ALLOWED_RECIPIENT=backup-7a3f9e2b4c1d8f6a@yourdomain.com \
  -e SMTP_ALLOWED_DOMAINS="example.com" \
  -e SMTP_REQUIRED_HEADERS="X-Original-To:name@example.com" \
  email-backup-server
```

**Environment Variables:**
- `SMTP_HOST`: Interface to bind to (default: 0.0.0.0)
- `SMTP_PORT`: Port to listen on (default: 2525)
- `SMTP_MAILDIR`: Path to store emails (default: /data/email)
- `SMTP_ALLOWED_RECIPIENT`: Only accept emails to this address
- `SMTP_ALLOWED_DOMAINS`: Space-separated list of sender domains
- `SMTP_REQUIRED_HEADERS`: Comma-separated list of required headers (format: "Header:value,Header2:value2")
- `SMTP_DISABLE_SPF`: Set to `true`, `1`, or `yes` to disable SPF validation

## Finding Sender Domains

To find what sender domains to whitelist in `--allowed-domains`:

1. **Check your email provider's documentation** for forwarding configuration
2. **Send a test email** and check server logs for the rejected sender domain
3. **Examine email headers** from previously forwarded emails (look at `From:` or `Return-Path:`)

## DNS Setup

Configure these DNS records to receive email:

**1. A Record** (points mail subdomain to your server):
```
Type: A
Host: mail
Value: YOUR_PUBLIC_IP_ADDRESS
TTL: 3600
```

**2. MX Record** (tells where to deliver email):
```
Type: MX
Host: @
Value: mail.yourdomain.com
Priority: 10
TTL: 3600
```

**3. SPF Record** (recommended - prevents domain spoofing):
```
Type: TXT
Host: @
Value: "v=spf1 -all"
TTL: 3600
```

The `-all` hard-fails unauthorized senders, perfect for receive-only domains.

**Verify DNS:**
```bash
dig mail.yourdomain.com        # Should show your IP
dig MX yourdomain.com          # Should show mail.yourdomain.com
dig TXT yourdomain.com         # Should show SPF record
```

DNS propagation can take 5 minutes to 48 hours.

## Email Storage

Emails are stored in standard Maildir format at `~/email` (or your specified path):

```
email/
├── cur/     # Current messages
├── new/     # New unread messages
└── tmp/     # Temporary files
```

Each email is a separate file, searchable with standard tools (grep, etc.).

## Viewing Emails

Use the included email viewer to browse and search your backed-up emails:

```bash
# List recent emails
uv run email-viewer --maildir ~/email --list

# Limit number shown
uv run email-viewer --maildir ~/email --list --limit 10

# Search for text
uv run email-viewer --maildir ~/email --search "invoice"

# Interactive viewer
uv run email-viewer ~/email
```

**Docker:**
```bash
# List emails
docker exec -it email-backup email-viewer --maildir /data/email --list

# Search
docker exec -it email-backup email-viewer --maildir /data/email --search "text"
```

## Security

The server uses multiple layers of filtering:

1. **Recipient filtering**: Only accepts emails TO a specific random address
2. **Sender domain filtering**: Only accepts emails FROM whitelisted domains
3. **SPF validation** (enabled by default): Verifies the connecting IP is authorized by the sender's domain
4. **Header filtering** (optional): Validates specific email headers match expected values

Generate a random recipient address:
```bash
python3 -c "import secrets; print(f'{secrets.token_hex(16)}@yourdomain.com')"
```

**SPF Validation:**
Enabled by default, the server checks the sender's SPF DNS records to verify the connecting IP is authorized to send email for that domain. This prevents spoofing even if someone discovers your recipient address. Use `--disable-spf` to turn off (not recommended).

**Header Filtering:**
For forwarded emails, you can require specific headers to ensure the email was originally sent to your intended address. For example, `--required-header "X-Original-To:your@email.com"`

### Security Limitations

- **No TLS/STARTTLS**: Traffic is unencrypted
- **No authentication**: Server accepts anonymous connections (mitigated by filtering)
- **No rate limiting**: Vulnerable to DoS if recipient address is discovered
- **No size limits**: Large emails could fill disk
- **SPF not foolproof**: Assumes sender domains publish accurate SPF records
