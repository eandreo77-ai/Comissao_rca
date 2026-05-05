"""
Modelos Pydantic para o sistema de importação de comissões RCA
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import date


class ComissaoRCA(BaseModel):
    """Representa uma linha de comissão importada do Excel"""
    linha: int                          # Linha no Excel (para referência)
    parcela: int = 1                    # Número da parcela (1 ou 2)
    codusur: int                        # Código do RCA
    nome_rca: Optional[str] = None      # Nome do RCA (preenchido na validação)
    valor: float                        # Valor da comissão
    codconta: Optional[int] = None      # Conta contábil
    codfilial: Optional[str] = None     # Filial
    historico: Optional[str] = None     # Descrição/histórico
    dtvenc: Optional[date] = None       # Data de vencimento
    dtlanc: Optional[date] = None       # Data do lançamento


class ValidacaoItem(BaseModel):
    """Resultado da validação de uma linha"""
    linha: int
    codusur: int
    nome_rca: Optional[str] = None
    valor: float
    codconta: int
    codfilial: str
    historico: str
    dtvenc: Optional[date] = None
    dtlanc: Optional[date] = None
    valido: bool = True
    erros: List[str] = []
    avisos: List[str] = []


class ResultadoImportacao(BaseModel):
    """Resultado completo da importação/validação"""
    total_linhas: int = 0
    linhas_validas: int = 0
    linhas_com_erro: int = 0
    valor_total: float = 0.0
    itens: List[ValidacaoItem] = []
    erro_geral: Optional[str] = None


class ResultadoGravacao(BaseModel):
    """Resultado da gravação no banco"""
    sucesso: bool = False
    registros_gravados: int = 0
    recnums: List[int] = []
    erro: Optional[str] = None
