# =============================================================================
# Comissao RCA — imagem Docker (alvo: servidor Ubuntu 192.168.20.164)
# Base: Python 3.12-slim
# Instant Client: NÃO embutido (montado via volume do host /opt/oracle/instantclient_21_21)
# MariaDB:        NÃO embutido (usa MariaDB do host via network_mode: host)
# =============================================================================
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    TZ=America/Sao_Paulo

# ── Dependências do SO ──────────────────────────────────────────────────────
# libaio1: requerido pelo Oracle Instant Client (thick mode)
# libmariadb-dev: cabeçalhos do conector C, necessário pelo driver Python 'mariadb'
# build-essential: para compilar a wheel do driver mariadb
# curl: usado no healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        libaio1 \
        libmariadb-dev \
        build-essential \
        curl \
        ca-certificates \
        tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && rm -rf /var/lib/apt/lists/*

# ── ld.so vai procurar o Instant Client em /opt/instantclient (montado por volume) ──
RUN echo /opt/instantclient > /etc/ld.so.conf.d/oracle.conf

# ── App ─────────────────────────────────────────────────────────────────────
WORKDIR /code

COPY app/requirements.txt /code/app/requirements.txt
RUN pip install -r /code/app/requirements.txt

COPY app /code/app

# Streamlit lê algumas configs via env, outras via flags na CMD.
# server.address=127.0.0.1 + network_mode: host => acessível só via localhost do host
# (Nginx faz reverse proxy externamente)
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_ADDRESS=127.0.0.1 \
    STREAMLIT_SERVER_PORT=8502 \
    STREAMLIT_SERVER_ENABLE_CORS=false \
    STREAMLIT_SERVER_ENABLE_XSRF_PROTECTION=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

EXPOSE 8502

# Healthcheck — Streamlit expõe /_stcore/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fs http://127.0.0.1:8502/_stcore/health || exit 1

# ldconfig roda no entrypoint para registrar o Instant Client após o volume ser montado.
CMD ["sh", "-c", "ldconfig && exec streamlit run app/app.py --server.baseUrlPath=${APP_BASE_URL_PATH:-comissao}"]
