"""
Conexão e helpers de MariaDB compartilhados.
"""
from __future__ import annotations
import mariadb
from contextlib import contextmanager
from typing import Any, Iterable, Optional

from config import get_mariadb_config


# =============================================================================
# Conexão
# =============================================================================
def get_conn():
    """Cria uma conexão nova ao MariaDB. Sempre fechar com .close()."""
    cfg = get_mariadb_config()
    return mariadb.connect(
        host=cfg["host"],
        port=cfg["port"],
        user=cfg["user"],
        password=cfg["password"],
        database=cfg["database"],
        autocommit=False,
    )


@contextmanager
def conn_ctx():
    """Context manager: 'with conn_ctx() as conn:' — garante close."""
    conn = get_conn()
    try:
        yield conn
    finally:
        conn.close()


# =============================================================================
# Helpers de fetch (MariaDB-connector não suporta dictionary=True no cursor)
# =============================================================================
def _row_to_dict(cur, row):
    if not row:
        return None
    cols = [c[0] for c in cur.description]
    return dict(zip(cols, row))


def fetch_one(sql: str, params: Optional[Iterable[Any]] = None) -> Optional[dict]:
    """Retorna 1 row como dict, ou None."""
    with conn_ctx() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        row = cur.fetchone()
        return _row_to_dict(cur, row)


def fetch_all(sql: str, params: Optional[Iterable[Any]] = None) -> list[dict]:
    """Retorna todas as rows como lista de dicts."""
    with conn_ctx() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        cols = [c[0] for c in cur.description] if cur.description else []
        return [dict(zip(cols, r)) for r in rows]


def execute(sql: str, params: Optional[Iterable[Any]] = None) -> int:
    """Executa INSERT/UPDATE/DELETE e faz commit. Retorna lastrowid (para INSERT)."""
    with conn_ctx() as conn:
        cur = conn.cursor()
        cur.execute(sql, params or ())
        last_id = cur.lastrowid
        conn.commit()
        return last_id


def execute_many(sql: str, params_list: list[tuple]) -> None:
    """Executa em batch."""
    with conn_ctx() as conn:
        cur = conn.cursor()
        cur.executemany(sql, params_list)
        conn.commit()
