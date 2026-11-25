# syntax=docker/dockerfile:1.7

# Keep base images pinned by multi-platform manifest digest. Update these pins
# regularly to receive security fixes from upstream images.
FROM ghcr.io/astral-sh/uv:0.11.15@sha256:e590846f4776907b254ac0f44b5b380347af5d90d668138ca7938d1b0c2f98d3 AS uv

FROM python:3.14-slim-bookworm@sha256:e60ad028afdcdd14772a3d46decf0eaf616720f9102aeb4397a2045ff6718c3d AS builder

COPY --from=uv /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /build

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-project

FROM python:3.14-slim-bookworm@sha256:e60ad028afdcdd14772a3d46decf0eaf616720f9102aeb4397a2045ff6718c3d AS runtime

# Use a dated Debian snapshot so security updates stay repeatable for this
# pinned base image. The runtime never installs packages after startup.
RUN rm -f /etc/apt/sources.list.d/debian.sources \
    && printf 'Types: deb\nURIs: https://snapshot.debian.org/archive/debian/20261125T000000Z\nSuites: bookworm bookworm-updates\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\nCheck-Valid-Until: no\n' > /etc/apt/sources.list.d/debian.sources \
    && printf 'Types: deb\nURIs: https://snapshot.debian.org/archive/debian-security/20261125T000000Z\nSuites: bookworm-security\nComponents: main\nSigned-By: /usr/share/keyrings/debian-archive-keyring.gpg\nCheck-Valid-Until: no\n' > /etc/apt/sources.list.d/debian-security.sources \
    && DEBIAN_FRONTEND=noninteractive apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip uninstall -y pip

ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN install -d -o 10001 -g 10001 /data

COPY --from=builder --chown=0:0 /opt/venv /opt/venv
COPY --chown=0:0 app ./app
COPY --chown=0:0 alembic ./alembic
COPY --chown=0:0 alembic.ini ./alembic.ini

USER 10001:10001

EXPOSE 8000

STOPSIGNAL SIGTERM

HEALTHCHECK --interval=30s --timeout=3s --start-period=15s --retries=3 \
    CMD ["python", "-c", "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
