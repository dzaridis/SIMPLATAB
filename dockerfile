# syntax=docker/dockerfile:1.6
# ---------------------------------------------------------------------------
# Simplatab — EUCAIM processing-tool image.
# Multi-stage build:
#   * builder  -> compiles wheels into an isolated venv
#   * runtime  -> slim, non-root, read-only-input safe
# CPU-only stack (lightgbm / sklearn / xgboost). No CUDA needed.
# ---------------------------------------------------------------------------

# ---------- Stage 1: builder ----------
FROM python:3.9-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libgomp1 \
        ca-certificates \
        curl && \
    rm -rf /var/lib/apt/lists/*

# Build everything inside an isolated venv so transitive deps cannot be
# silently skipped by `pip install --prefix` shenanigans.
RUN python -m venv /opt/venv
ENV PATH=/opt/venv/bin:$PATH

COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r /tmp/requirements.txt

# ---------- Stage 2: runtime ----------
FROM python:3.9-slim AS runtime

LABEL name="simplatab" \
      version="1.1.0" \
      description="Simplatab — automated ML pipeline for tabular data (EUCAIM processing-tool)." \
      maintainer="Dimitrios Zaridis <dimzaridis@gmail.com>" \
      authorization="This Dockerfile is intended to build a container image that will be publicly accessible in the EUCAIM images repository." \
      org.opencontainers.image.title="simplatab" \
      org.opencontainers.image.description="Automated ML pipeline (binary + multiclass tabular data) with bias assessment, k-fold CV, threshold optimisation and SHAP explainability." \
      org.opencontainers.image.source="https://github.com/eucaim/simplatab-machine-learning-automator" \
      org.opencontainers.image.revision="main" \
      org.opencontainers.image.version="1.1.0" \
      org.opencontainers.image.licenses="EUPL-1.2" \
      org.opencontainers.image.vendor="EUCAIM" \
      org.opencontainers.image.authors="Dimitrios Zaridis <dimzaridis@gmail.com>"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/opt/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PYTHONPATH=/app \
    APP_DIR=/app \
    SIMPLATAB_OUTPUT_DIR=/output/Materials

ARG USER_UID=2323
ARG USER_GID=2323

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 \
        ca-certificates && \
    /usr/sbin/groupadd -g ${USER_GID} eucaim && \
    /usr/sbin/useradd  -r -u ${USER_UID} -g eucaim -d /home/eucaim -m -s /usr/sbin/nologin eucaim && \
    rm -rf /var/lib/apt/lists/*

# Copy the prebuilt venv from the builder stage.
COPY --from=builder /opt/venv /opt/venv

WORKDIR /app

# Copy application code. Keep large/optional folders (Examples) out of the
# image — see .dockerignore.
COPY Helpers        /app/Helpers
COPY templates      /app/templates
COPY static         /app/static
COPY tests          /app/tests
COPY app.py         /app/app.py
COPY __main__.py    /app/__main__.py
COPY healthcheck.py /app/healthcheck.py
COPY entrypoint.sh  /app/entrypoint.sh

# EUCAIM convention: read-only /input, writable /output.
RUN mkdir -p /input /output /tmp /app && \
    chmod +x /app/entrypoint.sh && \
    chown -R root:eucaim /app /opt/venv /input /output && \
    chmod -R 755 /app /opt/venv && \
    chmod -R 775 /output && \
    chmod 555 /input

USER eucaim

EXPOSE 5000

HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python /app/healthcheck.py || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD []
