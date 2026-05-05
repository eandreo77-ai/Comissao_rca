# =============================================================================
# Comissao RCA — imagem Docker do app Streamlit
# Base: Python 3.12-slim (Debian Bookworm)
# Inclui: Oracle Instant Client (basic-lite) para thick mode + libaio
# =============================================================================
FROM python:3.12-slim AS base

ARG INSTANTCLIENT_VERSION=21.13.0.0.0
ARG INSTANTCLIENT_ZIP=instantclient-basiclite-linux.x64-${INSTANTCLIENT_VERSION}dbru.zip
ARG INSTANTCLIENT_URL=https://download.oracle.com/otn_software/linux/instantclient/2113000/${INSTANTCLIENT_ZIP}

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    TZ=America/Sao_Paulo

# ── Dependências do SO ──────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        unzip \
        libaio1 \
        ca-certificates \
        tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && rm -rf /var/lib/apt/lists/*

# ── Oracle Instant Client (thick mode obrigatório p/ Oracle 11g) ───────────
RUN mkdir -p /opt/instantclient \
    && cd /tmp \
    && curl -fSL "${INSTANTCLIENT_URL}" -o ic.zip \
    && unzip -q ic.zip -d /opt \
    && mv /opt/instantclient_*/* /opt/instantclient/ \
    && rmdir /opt/instantclient_* \
    && rm -f /tmp/ic.zip \
    && echo /opt/instantclient > /etc/ld.so.conf.d/oracle.conf \
    && ldconfig

# ── App ─────────────────────────────────────────────────────────────────────
WORKDIR /code

COPY app/requirements.txt /code/app/requirements.txt
RUN pip install -r /code/app/requirements.txt

COPY app /code/app

# Streamlit lê algumas configs via env, outras via flags na CMD
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8501

# Healthcheck — Streamlit expõe /_stcore/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fs http://localhost:8501/_stcore/health || exit 1

# baseUrlPath é dinâmico (vem do .env), por isso não vai como ENV fixa
CMD ["sh", "-c", "exec streamlit run app/app.py --server.baseUrlPath=${APP_BASE_URL_PATH:-comissao}"]
