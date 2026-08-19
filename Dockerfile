FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_NO_DEV=1 \
    UV_LINK_MODE=copy \
    AUTOVD_HOST=0.0.0.0 \
    AUTOVD_PORT=8000 \
    AUTOVD_JOB_ROOT=/tmp/autovd-jobs \
    AUTOVD_MUSIC_DIR=/app/music/library

RUN apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=20 \
    && apt-get install --yes --no-install-recommends ca-certificates ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir "uv==0.12.5"

WORKDIR /app

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --locked --no-dev --no-editable \
    && useradd --create-home --uid 10001 autovd \
    && mkdir -p /tmp/autovd-jobs /app/music/library \
    && chown -R autovd:autovd /tmp/autovd-jobs /app/music

USER autovd

EXPOSE 8000
VOLUME ["/app/music/library"]

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('AUTOVD_PORT', '8000') + '/health', timeout=2).read()"

CMD ["/app/.venv/bin/autovd-mcp"]
