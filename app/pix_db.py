"""
Camada de persistência das chaves PIX dos RCAs.

Backend: MariaDB (tabelas `rca_pix` e `rca_ignorar` criadas pela migration 001).
Antes era SQLite local em app/data/pix.db.

Mantém a MESMA API pública da versão SQLite — a página de Cadastro_PIX
NÃO precisa mudar de linha alguma.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Optional

import pandas as pd

import db


TIPOS_VALIDOS = ("CPF", "CNPJ", "EMAIL", "TELEFONE", "ALEATORIA")


@dataclass
class RegistroPix:
    codrca:     int
    nome_rca:   str
    chave_pix:  str
    tipo_chave: str
    dt_atualizacao: Optional[str] = None
    usuario:        Optional[str] = None


# =============================================================================
# Compat: SQLite usava init_db() pra criar tabelas. No MariaDB já existem
# (criadas pela migration 001). Função vira no-op.
# =============================================================================
def init_db() -> None:
    pass


# =============================================================================
# CRUD de rca_pix
# =============================================================================
def listar() -> pd.DataFrame:
    rows = db.fetch_all(
        """
        SELECT codrca, nome_rca, chave_pix, tipo_chave,
               DATE_FORMAT(dt_atualizacao, '%Y-%m-%d %H:%i:%S') AS dt_atualizacao,
               usuario
          FROM rca_pix
         ORDER BY nome_rca
        """
    )
    return pd.DataFrame(rows or [])


def buscar(codrca: int) -> Optional[RegistroPix]:
    row = db.fetch_one(
        """
        SELECT codrca, nome_rca, chave_pix, tipo_chave,
               DATE_FORMAT(dt_atualizacao, '%Y-%m-%d %H:%i:%S') AS dt_atualizacao,
               usuario
          FROM rca_pix
         WHERE codrca = %s
        """,
        (int(codrca),),
    )
    if not row:
        return None
    return RegistroPix(**row)


def upsert(reg: RegistroPix, usuario: Optional[str] = None) -> None:
    erro = validar(reg)
    if erro:
        raise ValueError(erro)

    db.execute(
        """
        INSERT INTO rca_pix
          (codrca, nome_rca, chave_pix, tipo_chave, usuario)
        VALUES
          (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            nome_rca   = VALUES(nome_rca),
            chave_pix  = VALUES(chave_pix),
            tipo_chave = VALUES(tipo_chave),
            usuario    = VALUES(usuario)
        """,
        (
            int(reg.codrca),
            reg.nome_rca.strip(),
            reg.chave_pix.strip(),
            reg.tipo_chave.strip().upper(),
            usuario or reg.usuario,
        ),
    )


def upsert_lote(
    registros: Iterable[RegistroPix],
    usuario: Optional[str] = None,
) -> tuple[int, list[str]]:
    """Retorna (qtd_gravada, lista_de_erros)."""
    ok, erros = 0, []
    for r in registros:
        try:
            upsert(r, usuario)
            ok += 1
        except Exception as e:
            erros.append(f"CODRCA {r.codrca}: {e}")
    return ok, erros


def remover(codrca: int) -> None:
    db.execute("DELETE FROM rca_pix WHERE codrca = %s", (int(codrca),))


# =============================================================================
# Lista de ignorados
# =============================================================================
def listar_ignorados() -> pd.DataFrame:
    rows = db.fetch_all(
        """
        SELECT codrca, motivo,
               DATE_FORMAT(dt_inclusao, '%Y-%m-%d %H:%i:%S') AS dt_inclusao
          FROM rca_ignorar
         ORDER BY codrca
        """
    )
    return pd.DataFrame(rows or [])


def codigos_ignorados() -> set[int]:
    rows = db.fetch_all("SELECT codrca FROM rca_ignorar")
    return {int(r["codrca"]) for r in (rows or [])}


def adicionar_ignorado(codrca: int, motivo: str = "") -> None:
    db.execute(
        """
        INSERT INTO rca_ignorar (codrca, motivo)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE motivo = VALUES(motivo)
        """,
        (int(codrca), (motivo or "").strip()),
    )


def remover_ignorado(codrca: int) -> None:
    db.execute("DELETE FROM rca_ignorar WHERE codrca = %s", (int(codrca),))


# =============================================================================
# Validação (idêntica ao backend SQLite — regras de negócio não mudaram)
# =============================================================================
_RE_DIGITS  = re.compile(r"\D+")
_RE_EMAIL   = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_RE_ALEAT   = re.compile(r"^[0-9a-fA-F-]{32,36}$")


def _so_digitos(v: str) -> str:
    return _RE_DIGITS.sub("", v or "")


def validar(reg: RegistroPix) -> Optional[str]:
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


# =============================================================================
# Importação de planilha (DataFrame → list[RegistroPix])
# =============================================================================
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
    """Converte DataFrame da planilha em lista de RegistroPix + avisos."""
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
