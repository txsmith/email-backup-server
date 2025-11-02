#!/bin/bash
set -e

# Build command with environment variables
CMD="email-backup-server"

# Add host
CMD="$CMD --host ${SMTP_HOST:-0.0.0.0}"

# Add port
CMD="$CMD --port ${SMTP_PORT:-2525}"

# Add maildir
CMD="$CMD --maildir ${SMTP_MAILDIR:-/data/email}"

# Add allowed recipient if set
if [ -n "$SMTP_ALLOWED_RECIPIENT" ]; then
    CMD="$CMD --allowed-recipient $SMTP_ALLOWED_RECIPIENT"
fi

# Add allowed domains if set
if [ -n "$SMTP_ALLOWED_DOMAINS" ]; then
    CMD="$CMD --allowed-domains $SMTP_ALLOWED_DOMAINS"
fi

# Disable SPF validation if requested
if [ "$SMTP_DISABLE_SPF" = "true" ] || [ "$SMTP_DISABLE_SPF" = "1" ] || [ "$SMTP_DISABLE_SPF" = "yes" ]; then
    CMD="$CMD --disable-spf"
fi

# Add required headers if set (comma-separated list)
if [ -n "$SMTP_REQUIRED_HEADERS" ]; then
    IFS=',' read -ra HEADERS <<< "$SMTP_REQUIRED_HEADERS"
    for header in "${HEADERS[@]}"; do
        CMD="$CMD --required-header \"$header\""
    done
fi

# Execute the command
exec $CMD
