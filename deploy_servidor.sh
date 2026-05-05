#!/usr/bin/env bash
# =============================================================================
# Comissao RCA — Deploy no servidor Ubuntu 192.168.20.164
#
# Pré-requisitos confirmados pelo diagnóstico:
#   - Docker 29.3.1 (rofe sem sudo)
#   - MariaDB 10.11 nativo, bind 127.0.0.1, sudo sem senha
#   - Instant Client em /opt/oracle/instantclient_21_21
#   - Nginx 1.24 instalado, default + suprimentos.conf existentes
#   - Conectividade Oracle 192.168.0.172:1521 OK
#
# Como rodar:
#   chmod +x deploy_servidor.sh
#   ./deploy_servidor.sh
#
# O script é idempotente: pode ser re-rodado sem quebrar.
# Para cada etapa, sai imediatamente em erro (set -e).
# =============================================================================
set -euo pipefail

# ── Variáveis (ajuste aqui se necessário) ──────────────────────────────────
INSTALL_DIR="/opt/comissao-rca"
REPO_URL="https://github.com/eandreo77-ai/Comissao_rca.git"

# Senha do MariaDB e secret da app: usa .env existente, ou gera novos.
ENV_FILE="$INSTALL_DIR/.env"
if [ -f "$ENV_FILE" ] && grep -q "^MARIADB_PASSWORD=" "$ENV_FILE"; then
    MARIADB_PASS="$(grep '^MARIADB_PASSWORD=' "$ENV_FILE" | cut -d= -f2-)"
    APP_SECRET="$(grep '^APP_SECRET=' "$ENV_FILE" | cut -d= -f2- || true)"
fi
[ -z "${MARIADB_PASS:-}" ] && MARIADB_PASS="$(openssl rand -base64 24 | tr -d '+/' | cut -c1-32)"
[ -z "${APP_SECRET:-}" ]   && APP_SECRET="$(openssl rand -base64 32)"

# Cor pra logs
C_TIT='\033[1;36m'
C_OK='\033[0;32m'
C_WARN='\033[0;33m'
C_END='\033[0m'

step() { echo ""; echo -e "${C_TIT}━━ $1 ━━${C_END}"; }
ok()   { echo -e "  ${C_OK}✓${C_END} $1"; }
warn() { echo -e "  ${C_WARN}!${C_END} $1"; }

echo "================================================================"
echo " COMISSAO RCA — DEPLOY"
echo " Server:    $(hostname) ($(hostname -I | awk '{print $1}'))"
echo " Install:   $INSTALL_DIR"
echo " Repo:      $REPO_URL"
echo "================================================================"

# ── 1. Diretório de instalação ──────────────────────────────────────────────
step "1. Diretório /opt/comissao-rca"
sudo mkdir -p "$INSTALL_DIR"
sudo chown rofe:rofe "$INSTALL_DIR"
ok "$(stat -c '%n owner=%U' $INSTALL_DIR)"

# ── 2. Clone (ou pull se já existe) ─────────────────────────────────────────
step "2. Repo do GitHub"
if [ -d "$INSTALL_DIR/.git" ]; then
    cd "$INSTALL_DIR"
    git pull origin main
    ok "git pull em repo existente"
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    ok "git clone novo"
fi
cd "$INSTALL_DIR"
git --no-pager log --oneline -3

# ── 3. MariaDB: database + usuário ──────────────────────────────────────────
step "3. Database e usuário no MariaDB do host"
sudo mariadb <<EOF
CREATE DATABASE IF NOT EXISTS comissao_rca
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'comissao'@'localhost' IDENTIFIED BY '$MARIADB_PASS';
CREATE USER IF NOT EXISTS 'comissao'@'127.0.0.1' IDENTIFIED BY '$MARIADB_PASS';
ALTER USER 'comissao'@'localhost' IDENTIFIED BY '$MARIADB_PASS';
ALTER USER 'comissao'@'127.0.0.1' IDENTIFIED BY '$MARIADB_PASS';
GRANT ALL PRIVILEGES ON comissao_rca.* TO 'comissao'@'localhost';
GRANT ALL PRIVILEGES ON comissao_rca.* TO 'comissao'@'127.0.0.1';
FLUSH PRIVILEGES;
EOF
ok "database 'comissao_rca' + usuário 'comissao' OK"
sudo mariadb -e "SHOW DATABASES LIKE 'comissao_rca'; SELECT User, Host FROM mysql.user WHERE User='comissao';"

# ── 4. Aplicar schema ───────────────────────────────────────────────────────
step "4. Schema (migrations/001_initial.sql)"
sudo mariadb < "$INSTALL_DIR/migrations/001_initial.sql"
ok "schema aplicado"
sudo mariadb -e "USE comissao_rca; SHOW TABLES;"

# ── 5. .env (só cria se não existir) ────────────────────────────────────────
step "5. Arquivo .env"
ENV_FILE="$INSTALL_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    warn ".env já existe, preservado: $ENV_FILE"
else
    cat > "$ENV_FILE" <<ENVEOF
APP_PORT=8502
APP_BASE_URL_PATH=comissao
APP_SECRET=$APP_SECRET

ORACLE_USER=TESTE
ORACLE_PASSWORD=TESTE
ORACLE_DSN=(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=192.168.0.172)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=BDTESTE)))
ORACLE_INSTANTCLIENT_DIR=/opt/instantclient

MARIADB_HOST=127.0.0.1
MARIADB_PORT=3306
MARIADB_DATABASE=comissao_rca
MARIADB_USER=comissao
MARIADB_PASSWORD=$MARIADB_PASS
ENVEOF
    chmod 600 "$ENV_FILE"
    ok ".env criado, chmod 600"
fi

# ── 6. Conectividade do MariaDB usando o usuário comissao ──────────────────
step "6. Teste de conexão MariaDB com usuário 'comissao'"
mariadb -h 127.0.0.1 -u comissao -p"$MARIADB_PASS" -e "USE comissao_rca; SHOW TABLES;" 2>&1
ok "conexão validada"

# ── 7. Build da imagem Docker ───────────────────────────────────────────────
step "7. Build da imagem Docker (1ª vez ~3-5min)"
cd "$INSTALL_DIR"
docker compose build
ok "build OK"

# ── 8. Sobe o container ─────────────────────────────────────────────────────
step "8. docker compose up -d"
docker compose up -d
ok "container subiu"
docker compose ps

# ── 9. Logs iniciais ────────────────────────────────────────────────────────
step "9. Logs iniciais (5s pra Streamlit subir)"
sleep 5
docker compose logs --tail=30

# ── 10. Healthcheck Streamlit ───────────────────────────────────────────────
step "10. Healthcheck do Streamlit (porta 8502)"
sleep 3
if curl -fsS http://127.0.0.1:8502/_stcore/health 2>/dev/null; then
    ok "Streamlit respondendo"
else
    warn "Streamlit ainda não respondeu — veja docker compose logs"
fi

# ── 11. Configura Nginx ─────────────────────────────────────────────────────
step "11. Nginx — instala comissao.conf"
sudo cp "$INSTALL_DIR/nginx/comissao.conf" /etc/nginx/sites-available/comissao.conf
if [ ! -L /etc/nginx/sites-enabled/comissao.conf ]; then
    sudo ln -s /etc/nginx/sites-available/comissao.conf /etc/nginx/sites-enabled/comissao.conf
    ok "symlink criado em sites-enabled"
else
    ok "symlink já existia"
fi
sudo nginx -t
sudo systemctl reload nginx
ok "nginx recarregado"

# ── 12. Teste final via Nginx ───────────────────────────────────────────────
step "12. Teste final (via Nginx)"
sleep 2
if curl -fsS http://127.0.0.1/comissao/_stcore/health 2>/dev/null; then
    ok "Streamlit respondendo VIA NGINX"
else
    warn "Não respondeu pelo nginx — veja journalctl -u nginx -n 20"
fi

echo ""
echo "================================================================"
echo -e "${C_OK} DEPLOY CONCLUÍDO ${C_END}"
echo "================================================================"
echo " Acesse:"
echo "   http://192.168.20.164/comissao/"
echo "   http://rofe.app/comissao/        (depois de cadastrar DNS interno)"
echo ""
echo " Logs:        docker compose -f $INSTALL_DIR/docker-compose.yml logs -f"
echo " Restart:     docker compose -f $INSTALL_DIR/docker-compose.yml restart"
echo " Stop:        docker compose -f $INSTALL_DIR/docker-compose.yml down"
echo "================================================================"
