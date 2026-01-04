# Production Dockerfile for Meta Agent MCP Server
# Uses multi-stage build for smaller image size
# Includes Playwright for web crawling capabilities

FROM python:3.12-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

# Install the package
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# --- Production Stage ---
FROM python:3.12-slim AS production

# Install Playwright system dependencies and runtime tools
# These are required for Chromium to run in the container
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    # Playwright/Chromium dependencies
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libatspi2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Playwright browsers (as root, before switching user)
# This installs Chromium which is used by crawl4ai
RUN playwright install chromium && \
    playwright install-deps chromium

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash mcpuser

# Copy Playwright browsers to user-accessible location
# Playwright installs to /root/.cache by default, we need to make it accessible
RUN mkdir -p /home/mcpuser/.cache && \
    cp -r /root/.cache/ms-playwright /home/mcpuser/.cache/ && \
    chown -R mcpuser:mcpuser /home/mcpuser/.cache

USER mcpuser
WORKDIR /home/mcpuser/app

# Set Playwright browser path
ENV PLAYWRIGHT_BROWSERS_PATH=/home/mcpuser/.cache/ms-playwright

# Copy application code
COPY --chown=mcpuser:mcpuser src ./src

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LOG_LEVEL=INFO

# Default to SSE transport for Docker (HTTP-based)
ENV TRANSPORT=sse
ENV TRANSPORT_HOST=0.0.0.0
ENV TRANSPORT_PORT=8080

# Expose the MCP server port
EXPOSE 8080

# Health check using our custom /health endpoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the server (uses TRANSPORT, TRANSPORT_HOST, TRANSPORT_PORT env vars via config)
CMD ["python", "-m", "meta_agent_mcp.server"]
