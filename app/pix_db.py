"""
Camada de persistência das chaves PIX dos RCAs.

Hoje: SQLite local (arquivo em app/data/pix.db).
Futuro: trocar a implementação por MariaDB/Django mantendo a mesma API pública.
"""
from __future__ import annotations

import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable

import pandas as pd

DB_DIR  = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "pix.db")

TIPOS_VALIDOS = ("CPF", "CNPJ", "EMAIL", "TELEFONE", "ALEATORIA")


@dataclass
class RegistroPix:
    codrca:     int
    nome_rca:   str
    chave_pix:  str
    tipo_chave: str
    dt_atualizacao: str | None = None
    usuario:        str | None = None


# ─────────────────────────────────────────────
# Conexão / schema
# ─────────────────────────────────────────────
def _ensure_dir() -> None:
    os.makedirs(DB_DIR, exist_ok=True)


@contextmanager
def _conn():
    _ensure_dir()
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def init_db() -> None:
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS rca_pix (
                codrca         INTEGER PRIMARY KEY,
                nome_rca       TEXT    NOT NULL,
                chave_pix      TEXT    NOT NULL,
                tipo_chave     TEXT    NOT NULL,
                dt_atualizacao TEXT    NOT NULL,
                usuario        TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS rca_ignorar (
                codrca       INTEGER PRIMARY KEY,
                motivo       TEXT    NOT NULL DEFAULT '',
                dt_inclusao  TEXT    NOT NULL
            )
        """)


# ─────────────────────────────────────────────
# Lista de ignorados (testers / usuários internos)
# ─────────────────────────────────────────────
def listar_ignorados() -> pd.DataFrame:
    init_db()
    with _conn() as con:
        return pd.read_sql_query(
            "SELECT codrca, motivo, dt_inclusao FROM rca_ignorar ORDER BY codrca", con,
        )


def codigos_ignorados() -> set[int]:
    init_db()
    with _conn() as con:
        rows = con.execute("SELECT codrca FROM rca_ignorar").fetchall()
    return {int(r[0]) for r in rows}


def adicionar_ignorado(codrca: int, motivo: str = "") -> None:
    init_db()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as con:
        con.execute("""
            INSERT INTO rca_ignorar (codrca, motivo, dt_inclusao) VALUES (?, ?, ?)
            ON CONFLICT(codrca) DO UPDATE SET motivo = excluded.motivo
        """, (int(codrca), (motivo or "").strip(), agora))


def remover_ignorado(codrca: int) -> None:
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM rca_ignorar WHERE codrca = ?", (int(codrca),))


# ─────────────────────────────────────────────
# CRUD
# ─────────────────────────────────────────────
def listar() -> pd.DataFrame:
    init_db()
    with _conn() as con:
        df = pd.read_sql_query(
            "SELECT codrca, nome_rca, chave_pix, tipo_chave, dt_atualizacao, usuario "
            "FROM rca_pix ORDER BY nome_rca",
            con,
        )
    return df


def buscar(codrca: int) -> RegistroPix | None:
    init_db()
    with _conn() as con:
        row = con.execute(
            "SELECT codrca, nome_rca, chave_pix, tipo_chave, dt_atualizacao, usuario "
            "FROM rca_pix WHERE codrca = ?",
            (int(codrca),),
        ).fetchone()
    if not row:
        return None
    return RegistroPix(**dict(row))


def upsert(reg: RegistroPix, usuario: str | None = None) -> None:
    init_db()
    erro = validar(reg)
    if erro:
        raise ValueError(erro)

    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with _conn() as con:
        con.execute("""
            INSERT INTO rca_pix (codrca, nome_rca, chave_pix, tipo_chave, dt_atualizacao, usuario)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(codrca) DO UPDATE SET
                nome_rca       = excluded.nome_rca,
                chave_pix      = excluded.chave_pix,
                tipo_chave     = excluded.tipo_chave,
                dt_atualizacao = excluded.dt_atualizacao,
                usuario        = excluded.usuario
        """, (
            int(reg.codrca),
            reg.nome_rca.strip(),
            reg.chave_pix.strip(),
            reg.tipo_chave.strip().upper(),
            agora,
            usuario or reg.usuario,
        ))


def upsert_lote(registros: Iterable[RegistroPix], usuario: str | None = None) -> tuple[int, list[str]]:
    """Retorna (qtd_gravada, lista_de_erros)."""
    init_db()
    ok, erros = 0, []
    for r in registros:
        try:
            upsert(r, usuario)
            ok += 1
        except Exception as e:
            erros.append(f"CODRCA {r.codrca}: {e}")
    return ok, erros


def remover(codrca: int) -> None:
    init_db()
    with _conn() as con:
        con.execute("DELETE FROM rca_pix WHERE codrca = ?", (int(codrca),))


# ─────────────────────────────────────────────
# Validação
# ─────────────────────────────────────────────
_RE_DIGITS  = re.compile(r"\D+")
_RE_EMAIL   = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RE_ALEAT   = re.compile(r"^[0-9a-fA-F-]{32,36}$")


def _so_digitos(v: str) -> str:
    return _RE_DIGITS.sub("", v or "")


def validar(reg: RegistroPix) -> str | None:
    """Retorna mensagem de erro ou None se válido."""
    if not reg.codrca or int(reg.codrca) <= 0:
        return "CODRCA inválido"
    if not (reg.nome_rca or "").strip():
        return "Nome do RCA obrigatório"
    if not (reg.chave_pix or "").strip():
        return "Chave PIX obrigatória"

    tipo = (reg.tipo_chave or "").strip().upper()
    if tipo not in TIPOS_VALIDOS:
        return f"Tipo de chave inválido (use: {', '.join(TIPOS_VALIDOS)})"

    chave = reg.chave_pix.strip()
    if tipo == "CPF" and len(_so_digitos(chave)) != 11:
        return "CPF deve ter 11 dígitos"
    if tipo == "CNPJ" and len(_so_digitos(chave)) != 14:
        return "CNPJ deve ter 14 dígitos"
    if tipo == "EMAIL" and not _RE_EMAIL.match(chave):
        return "E-mail inválido"
    if tipo == "TELEFONE":
        d = _so_digitos(chave)
        if len(d) < 10 or len(d) > 13:
            return "Telefone deve ter entre 10 e 13 dígitos"
    if tipo == "ALEATORIA" and not _RE_ALEAT.match(chave.replace("-", "")):
        return "Chave aleatória inválida (esperado 32 caracteres hex)"
    return None


# ─────────────────────────────────────────────
# Importação de planilha
# ─────────────────────────────────────────────
_COLS_ALIAS = {
    "codrca":     {"codrca", "cod_rca", "codigo", "cod", "id_rca"},
    "nome_rca":   {"rca", "nome", "nome_rca", "representante"},
    "chave_pix":  {"pix", "chave_pix", "chave"},
    "tipo_chave": {"tipo_chave", "tipo", "tipochave"},
}


def _mapear_colunas(df: pd.DataFrame) -> dict[str, str]:
    mapping: dict[str, str] = {}
    cols_norm = {c: c.strip().lower().replace(" ", "_") for c in df.columns}
    for alvo, aliases in _COLS_ALIAS.items():
        for orig, norm in cols_norm.items():
            if norm in aliases:
                mapping[alvo] = orig
                break
    return mapping


def df_para_registros(df: pd.DataFrame) -> tuple[list[RegistroPix], list[str]]:
    """Converte DataFrame da planilha em lista de RegistroPix + lista de avisos."""
    avisos: list[str] = []
    cols = _mapear_colunas(df)
    faltando = [k for k in ("codrca", "nome_rca", "chave_pix", "tipo_chave") if k not in cols]
    if faltando:
        return [], [f"Colunas não encontradas: {', '.join(faltando)}"]

    regs: list[RegistroPix] = []
    for i, row in df.iterrows():
        try:
            cod = int(str(row[cols["codrca"]]).strip())
        except Exception:
            avisos.append(f"Linha {i+2}: CODRCA inválido — ignorada")
            continue
        regs.append(RegistroPix(
            codrca     = cod,
            nome_rca   = str(row[cols["nome_rca"]]).strip(),
            chave_pix  = str(row[cols["chave_pix"]]).strip(),
            tipo_chave = str(row[cols["tipo_chave"]]).strip().upper(),
        ))
    return regs, avisos
