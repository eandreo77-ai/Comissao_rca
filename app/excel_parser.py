"""
Módulo de leitura e parse da planilha Excel de comissões RCA.

Formato real da planilha:
  - Colunas fixas: parceiro(COD), RCA, contadebito, historico, ...
  - Colunas de parcelas: cabeçalho = DATA (ex: 13/03/2026), valor = R$ da parcela
  - A DTLANC não está na planilha — é informada pelo usuário no app

Para cada coluna cujo cabeçalho seja uma data válida, é gerado um lançamento
com dtvenc = essa data e valor = célula correspondente.
"""
import openpyxl
from datetime import date, datetime
from typing import List, Optional, Tuple
from io import BytesIO
from models import ComissaoRCA
from config import CODCONTA_PADRAO, CODFILIAL_PADRAO


def ler_excel(
    conteudo_bytes: bytes,
    codfilial_padrao: str = CODFILIAL_PADRAO,
) -> Tuple[List[ComissaoRCA], Optional[str]]:
    """
    Lê a planilha e retorna lista de ComissaoRCA.

    - Detecta automaticamente as colunas fixas pelo nome.
    - Detecta colunas de parcela pelo cabeçalho ser uma data.
    - Uma linha gera N lançamentos (um por coluna de data preenchida).

    Retorna: (lista_comissoes, erro)
    """
    try:
        wb = openpyxl.load_workbook(BytesIO(conteudo_bytes), read_only=True, data_only=True)
        ws = wb.active

        if ws is None:
            return [], "Planilha vazia ou não encontrada"

        # Ler cabeçalho
        header_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), None)
        if not header_row:
            return [], "Cabeçalho da planilha não encontrado"

        header = [v if isinstance(v, (datetime, date)) else (str(v).strip() if v is not None else "") for v in header_row]  # EXCEL_DATES_PATCH

        col_map, colunas_parcela = mapear_colunas(header)

        if "codusur" not in col_map:
            return [], f"Coluna CODUSUR / parceiro(COD) não encontrada. Colunas: {', '.join(h for h in header if h)}"

        if not colunas_parcela:
            return [], "Nenhuma coluna de data (parcela) encontrada no cabeçalho."

        comissoes = []
        for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            if row is None or all(v is None for v in row):
                continue

            codusur_val = get_cell_value(row, col_map.get("codusur"))
            if codusur_val is None:
                continue

            try:
                codusur = int(float(str(codusur_val)))
            except (ValueError, TypeError):
                continue

            nome_rca  = parse_str(get_cell_value(row, col_map.get("nome_rca"))) or ""
            codconta  = parse_int(get_cell_value(row, col_map.get("codconta"))) or CODCONTA_PADRAO
            codfilial = parse_str(get_cell_value(row, col_map.get("codfilial"))) or codfilial_padrao
            historico = parse_str(get_cell_value(row, col_map.get("historico"))) or "COMISSAO RCA"

            # Gera um lançamento por coluna de data que tiver valor
            for parcela_num, (col_idx, dtvenc) in enumerate(colunas_parcela, start=1):
                valor_val = get_cell_value(row, col_idx)
                if valor_val is None:
                    continue

                try:
                    valor = parse_valor(valor_val)
                except (ValueError, TypeError):
                    continue

                if valor <= 0:
                    continue

                comissoes.append(ComissaoRCA(
                    linha=row_num,
                    parcela=parcela_num,
                    codusur=codusur,
                    nome_rca=nome_rca,
                    valor=valor,
                    codconta=codconta,
                    codfilial=codfilial,
                    historico=historico,
                    dtvenc=dtvenc,
                ))

        wb.close()

        if not comissoes:
            return [], "Nenhum lançamento encontrado. Verifique se as colunas de data possuem valores."

        return comissoes, None

    except Exception as e:
        return [], f"Erro ao ler planilha: {str(e)}"


def mapear_colunas(header: List[str]) -> Tuple[dict, List[Tuple[int, date]]]:
    """
    Retorna:
      col_map         → {campo: índice_coluna} para colunas fixas
      colunas_parcela → [(índice_coluna, date), ...] para colunas cujo cabeçalho é uma data
    """
    aliases = {
        "codusur":   ["PARCEIRO(COD)", "PARCEIRO", "CODUSUR", "COD_USUR",
                      "CODIGO_RCA", "COD_RCA", "RCA_COD", "CODRCA", "COD"],
        "nome_rca":  ["RCA", "NOME_RCA", "NOME RCA", "NOME", "PARCEIRO_NOME"],
        "codconta":  ["CONTADEBITO", "CONTA DEBITO", "CONTA_DEBITO",
                      "CODCONTA", "COD_CONTA", "CONTA", "CODIGO_CONTA"],
        "codfilial": ["CODFILIAL", "COD_FILIAL", "FILIAL", "CODIGO_FILIAL"],
        "historico": ["HISTORICO", "HISTÓRICO", "DESCRICAO", "DESCRIÇÃO", "OBS"],
    }

    col_map = {}
    colunas_parcela = []

    for idx, col_name in enumerate(header):
        # EXCEL_DATES_PATCH: se cabeçalho é datetime/date, é coluna de parcela
        if isinstance(col_name, (datetime, date)):
            _dt = col_name.date() if isinstance(col_name, datetime) else col_name
            colunas_parcela.append((idx, _dt))
            continue
        if not isinstance(col_name, str):
            continue
        col_upper = col_name.strip().upper()

        # Tenta casar com colunas fixas
        mapeado = False
        for campo, nomes in aliases.items():
            if col_upper in nomes and campo not in col_map:
                col_map[campo] = idx
                mapeado = True
                break

        # Se não mapeou, tenta interpretar como data (coluna de parcela)
        if not mapeado and col_name.strip():
            dt = parse_date(col_name.strip())
            if dt is not None:
                colunas_parcela.append((idx, dt))

    return col_map, colunas_parcela


def get_cell_value(row: tuple, idx: Optional[int]):
    if idx is None or idx >= len(row):
        return None
    return row[idx]


def parse_valor(val) -> float:
    """Converte valor monetário para float (aceita R$, ponto de milhar, vírgula decimal)."""
    if isinstance(val, (int, float)):
        return float(val)
    texto = str(val).strip()
    texto = texto.replace("R$", "").replace(" ", "")
    # Se tiver vírgula como separador decimal (formato BR: 7.219,48)
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:
        texto = texto.replace(",", ".")
    return float(texto)


def parse_int(val) -> Optional[int]:
    if val is None:
        return None
    try:
        return int(float(str(val)))
    except (ValueError, TypeError):
        return None


def parse_str(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s and s.upper() not in ("NONE", "NAN") else None


def parse_date(val) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    texto = str(val).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):  # EXCEL_DATES_PATCH
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None
