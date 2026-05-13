"""
Módulo de leitura e parse da planilha Excel de comissões RCA.

Formato da planilha (sem colunas de data):
  - parceiro(COD)  CODUSUR do RCA
  - RCA            nome (opcional)
  - contadebito    conta contábil (opcional, default CODCONTA_PADRAO)
  - historico      descrição do lançamento (opcional)
  - VALOR          valor total da comissão

Regra de parcelamento (definida pelo app, não pela planilha):
  - valor <= LIMITE_PARCELA_UNICA  → 1 lançamento com dt_parcela_1
  - valor > LIMITE_PARCELA_UNICA   → 2 lançamentos (valor/2 cada)
                                     parcela 1: round(valor/2, 2)  com dt_parcela_1
                                     parcela 2: valor - parcela 1   com dt_parcela_2

A data de vencimento é informada pelo USUÁRIO no app (não vem da planilha).
"""
from __future__ import annotations

import openpyxl
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from io import BytesIO
from typing import List, Optional, Tuple

from models import ComissaoRCA
from config import CODCONTA_PADRAO, CODFILIAL_PADRAO


def _meio_arredondar_cima(valor_total: float) -> float:
    """Retorna valor_total/2 com ROUND_HALF_UP na 2ª casa decimal.

    Exemplo:
      2.219,49 / 2 = 1.109,745  → 1.109,75  (pra cima)
      2.219,48 / 2 = 1.109,74   → 1.109,74
    """
    metade = Decimal(str(valor_total)) / Decimal(2)
    return float(metade.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


# Limite (R$) abaixo do qual o lançamento NÃO é parcelado.
LIMITE_PARCELA_UNICA = 2000.00


# =============================================================================
# Entrypoint
# =============================================================================
def ler_excel(
    conteudo_bytes: bytes,
    dt_parcela_1: date,
    dt_parcela_2: date,
    historico: str = "COMISSAO RCA",
    codfilial_padrao: str = CODFILIAL_PADRAO,
    limite_parcela_unica: float = LIMITE_PARCELA_UNICA,
) -> Tuple[List[ComissaoRCA], Optional[str]]:
    """Lê a planilha e retorna lista de ComissaoRCA aplicando a regra de parcelamento.

    Args:
        conteudo_bytes:       bytes do arquivo .xlsx
        dt_parcela_1:         data de vencimento da 1ª parcela (sempre usada)
        dt_parcela_2:         data da 2ª parcela (só usada se valor > limite)
        historico:            texto do histórico (igual pra todos os lançamentos)
        codfilial_padrao:     filial default se a coluna não vier na planilha
        limite_parcela_unica: acima desse valor (R$), divide em 2 parcelas

    Retorna:
        (lista_de_lancamentos, mensagem_de_erro_ou_None)
    """
    try:
        wb = openpyxl.load_workbook(BytesIO(conteudo_bytes), read_only=True, data_only=True)
        ws = wb.active

        if ws is None:
            return [], "Planilha vazia ou não encontrada"

        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
        if not header_row:
            return [], "Cabeçalho da planilha não encontrado"

        header = [
            str(v).strip() if v is not None else ""
            for v in header_row
        ]

        col_map = _mapear_colunas(header)

        if "codusur" not in col_map:
            return [], (
                f"Coluna CODUSUR / parceiro(COD) não encontrada. "
                f"Colunas detectadas: {', '.join(h for h in header if h)}"
            )

        if "valor" not in col_map:
            return [], (
                f"Coluna VALOR não encontrada. "
                f"Esperava uma coluna com nome 'VALOR' ou 'VALOR_TOTAL'. "
                f"Colunas detectadas: {', '.join(h for h in header if h)}"
            )

        comissoes: List[ComissaoRCA] = []

        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if row is None or all(v is None for v in row):
                continue

            codusur_val = _get_cell(row, col_map.get("codusur"))
            if codusur_val is None:
                continue
            try:
                codusur = int(float(str(codusur_val)))
            except (ValueError, TypeError):
                continue

            valor_val = _get_cell(row, col_map.get("valor"))
            if valor_val is None:
                continue
            try:
                valor_total = _parse_valor(valor_val)
            except (ValueError, TypeError):
                continue
            if valor_total <= 0:
                continue

            # Nome do RCA é buscado depois no Oracle (CODUSUR). Aqui só
            # mantém vazio se a planilha não trouxer.
            nome_rca  = _parse_str(_get_cell(row, col_map.get("nome_rca"))) or ""
            # Conta contábil: opcional na planilha; default do .env/config
            codconta  = _parse_int(_get_cell(row, col_map.get("codconta"))) or CODCONTA_PADRAO
            codfilial = _parse_str(_get_cell(row, col_map.get("codfilial"))) or codfilial_padrao
            # Histórico: SEMPRE do parâmetro (digitado no app pelo usuário).
            # Ignora qualquer coluna 'historico' da planilha.
            historico_linha = historico

            # ── Aplica regra de parcelamento ────────────────────────────────
            if valor_total <= limite_parcela_unica:
                # Parcela única — usa data 1
                comissoes.append(ComissaoRCA(
                    linha=row_num,
                    parcela=1,
                    codusur=codusur,
                    nome_rca=nome_rca,
                    valor=round(valor_total, 2),
                    codconta=codconta,
                    codfilial=codfilial,
                    historico=historico_linha,
                    dtvenc=dt_parcela_1,
                ))
            else:
                # 2 parcelas: p1 = metade arredondada PRA CIMA (ROUND_HALF_UP)
                # p2 = total - p1 (garante soma exata)
                valor_p1 = _meio_arredondar_cima(valor_total)
                valor_p2 = round(valor_total - valor_p1, 2)
                comissoes.append(ComissaoRCA(
                    linha=row_num,
                    parcela=1,
                    codusur=codusur,
                    nome_rca=nome_rca,
                    valor=valor_p1,
                    codconta=codconta,
                    codfilial=codfilial,
                    historico=historico_linha,
                    dtvenc=dt_parcela_1,
                ))
                comissoes.append(ComissaoRCA(
                    linha=row_num,
                    parcela=2,
                    codusur=codusur,
                    nome_rca=nome_rca,
                    valor=valor_p2,
                    codconta=codconta,
                    codfilial=codfilial,
                    historico=historico_linha,
                    dtvenc=dt_parcela_2,
                ))

        wb.close()

        if not comissoes:
            return [], "Nenhum lançamento encontrado. Verifique se a coluna VALOR possui valores positivos."

        return comissoes, None

    except Exception as e:
        return [], f"Erro ao ler planilha: {e}"


# =============================================================================
# Mapeamento de colunas (só fixas — sem detecção de data)
# =============================================================================
_ALIASES = {
    "codusur":   ["PARCEIRO(COD)", "PARCEIRO", "CODUSUR", "COD_USUR",
                  "CODIGO_RCA", "COD_RCA", "RCA_COD", "CODRCA", "COD"],
    "nome_rca":  ["RCA", "NOME_RCA", "NOME RCA", "NOME", "PARCEIRO_NOME"],
    "codconta":  ["CONTADEBITO", "CONTA DEBITO", "CONTA_DEBITO",
                  "CODCONTA", "COD_CONTA", "CONTA", "CODIGO_CONTA"],
    "codfilial": ["CODFILIAL", "COD_FILIAL", "FILIAL", "CODIGO_FILIAL"],
    "historico": ["HISTORICO", "HISTÓRICO", "DESCRICAO", "DESCRIÇÃO", "OBS"],
    "valor":     ["VALOR", "VALOR_TOTAL", "VALORTOTAL", "VALOR TOTAL",
                  "TOTAL", "VALOR_COMISSAO", "COMISSAO"],
}


def _mapear_colunas(header: List[str]) -> dict:
    col_map: dict = {}
    for idx, col_name in enumerate(header):
        if not col_name:
            continue
        col_upper = col_name.strip().upper()
        for campo, nomes in _ALIASES.items():
            if col_upper in nomes and campo not in col_map:
                col_map[campo] = idx
                break
    return col_map


# =============================================================================
# Helpers
# =============================================================================
def _get_cell(row: tuple, idx: Optional[int]):
    if idx is None or idx >= len(row):
        return None
    return row[idx]


def _parse_valor(val) -> float:
    """Converte valor monetário para float (aceita R$, ponto de milhar, vírgula decimal)."""
    if isinstance(val, (int, float)):
        return float(val)
    texto = str(val).strip()
    texto = texto.replace("R$", "").replace(" ", "")
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    return float(texto)


def _parse_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(float(str(val)))
    except (ValueError, TypeError):
        return None


def _parse_str(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s.upper() not in ("NONE", "NAN") else None
