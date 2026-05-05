"""
Configurações do sistema de comissões RCA — Rotina 749.
Carrega variáveis sensíveis do .env (raiz do projeto, um nível acima de app/).

Política de validação:
  - ORACLE_*, ORACLE_INSTANTCLIENT_DIR, APP_SECRET: erro fatal no import (sempre necessários)
  - MARIADB_*: lazy via get_mariadb_config() — só erra quando alguém chama
  - Valores fixos de negócio (CODCONTA, CODFILIAL, etc.): default sensato + override por env

Compatibilidade:
  Mantém os símbolos ORACLE_CONFIG, INSTANTCLIENT_PATH, ROTINA_749, CODCONTA_PADRAO,
  CODFILIAL_PADRAO, TIPOSERVICO no nível do módulo — assim app.py e oracle_db.py
  não precisam ser alterados.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# =============================================================================
# 1. Carregamento do .env (raiz do projeto)
# =============================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

try:
    from dotenv import load_dotenv
    if ENV_FILE.exists():
        load_dotenv(ENV_FILE, override=False)
except ImportError:
    # python-dotenv não instalado: confia que env vars vêm do shell/Docker.
    if ENV_FILE.exists():
        print(
            f"[config] AVISO: python-dotenv não instalado; .env existe em "
            f"{ENV_FILE} mas NÃO será carregado. Rode: pip install python-dotenv",
            file=sys.stderr,
        )


# =============================================================================
# 2. Helpers
# =============================================================================
def _required(var: str) -> str:
    """Retorna o valor da var ou aborta com mensagem clara."""
    val = os.environ.get(var)
    if not val:
        raise RuntimeError(
            f"Variável de ambiente obrigatória '{var}' não definida.\n"
            f"Verifique o arquivo .env em: {ENV_FILE}\n"
            f"Use .env.example como modelo."
        )
    return val


def _opt(var: str, default: str) -> str:
    """Retorna o valor da var ou o default."""
    return os.environ.get(var, default)


# =============================================================================
# 3. ORACLE (sensível) — falha no import se faltar
# =============================================================================
ORACLE_CONFIG = {
    "user":     _required("ORACLE_USER"),
    "password": _required("ORACLE_PASSWORD"),
    "dsn":      _required("ORACLE_DSN"),
}

# Path do Instant Client (thick mode obrigatório p/ Oracle 11g)
# Em Windows: C:\instantclient-basic\instantclient_23_8
# Em Linux:   /opt/instantclient
INSTANTCLIENT_PATH = _required("ORACLE_INSTANTCLIENT_DIR")


# =============================================================================
# 4. APP — secret pra sessão Streamlit/cookies
# =============================================================================
APP_SECRET = _required("APP_SECRET")


# =============================================================================
# 5. MARIADB — lazy (não bloqueia import se não estiver disponível)
# =============================================================================
def get_mariadb_config() -> dict:
    """Retorna config do MariaDB. Erra se variáveis não estão setadas.

    Use esta função no momento da conexão, não no import. Permite que o app
    suba mesmo em ambientes sem MariaDB (ex: dev local Windows na fase atual).
    """
    return {
        "host":     _required("MARIADB_HOST"),
        "port":     int(_opt("MARIADB_PORT", "3306")),
        "user":     _required("MARIADB_USER"),
        "password": _required("MARIADB_PASSWORD"),
        "database": _required("MARIADB_DATABASE"),
    }


# =============================================================================
# 6. VALORES FIXOS DE NEGÓCIO (default seguro + override por env)
# Quando a tabela 'configuracoes' do MariaDB estiver disponível, ler de lá
# em vez destas constantes.
# =============================================================================
CODCONTA_PADRAO  = int(_opt("CODCONTA_PADRAO", "100010"))   # Conta contábil de comissão
CODFILIAL_PADRAO = _opt("CODFILIAL_PADRAO", "1")            # Filial padrão
TIPOSERVICO      = _opt("TIPOSERVICO",      "99")           # Tipo de serviço (99=Outros Pag.)


# =============================================================================
# 7. PARÂMETROS DA ROTINA 749 (constantes do contrato com Oracle/WinThor)
# Não vão pra .env — são parte do código, validados pelo tracer.
# =============================================================================
ROTINA_749 = {
    "CODROTINACAD":        749,
    "TIPOLANC":            "C",   # Crédito (contas a pagar)
    "TIPOPARCEIRO":        "R",   # R = RCA/Representante
    "INDICE":              "A",
    "MOEDA":               "R",   # Real
    "NFSERVICO":           "N",
    "UTILIZOURATEIOCONTA": "N",
    "PRCRATEIOUTILIZADO":  100,
    "REINFEVENTOR4040":    "N",
    # DUPLIC é dinâmico (igual ao número da parcela) — passado em str(parcela)
    "CODROTINAALT":        "A",
}
