FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim

RUN useradd -m -u 1000 emailbackup

WORKDIR /app

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY src/ ./src/

# Install the package and dependencies using uv
RUN uv pip install --system --no-cache .

# Copy entrypoint script
COPY docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Create maildir directory and set permissions
RUN mkdir -p /data/email && \
    chown -R emailbackup:emailbackup /data

USER emailbackup

ENV PYTHONUNBUFFERED=1
ENV SMTP_HOST=0.0.0.0
ENV SMTP_PORT=2525
ENV SMTP_MAILDIR=/data/email
# Optional: SMTP_ALLOWED_RECIPIENT, SMTP_ALLOWED_DOMAINS, SMTP_DISABLE_SPF, SMTP_REQUIRED_HEADERS

VOLUME ["/data/email"]

EXPOSE 2525

# Health check (uses SMTP_PORT env var)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import socket, os; port = int(os.getenv('SMTP_PORT', 2525)); s = socket.socket(); s.connect(('localhost', port)); s.close()" || exit 1

# Use entrypoint script
ENTRYPOINT ["./docker-entrypoint.sh"]
