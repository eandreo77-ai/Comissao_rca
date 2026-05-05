"""
Configurações do sistema de importação de comissões RCA - Rotina 749
"""

# =============================================================================
# INSTANT CLIENT — obrigatório para Oracle 11g (modo grosso)
# Aponte para a pasta que contém oci.dll
# =============================================================================
INSTANTCLIENT_PATH = r"C:\instantclient-basic\instantclient_23_8"

# =============================================================================
# CONEXÃO ORACLE
# DSN no formato completo (necessário para Oracle 11g)
# =============================================================================
ORACLE_CONFIG = {
    "user":    "TESTE",
    "password": "TESTE",
    "dsn": "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=192.168.0.172)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=BDTESTE)))",
}

# =============================================================================
# VALORES FIXOS DO NEGÓCIO
# =============================================================================
CODCONTA_PADRAO  = 100010   # Conta contábil de comissão — sempre 100010
CODFILIAL_PADRAO = "1"      # Filial — sempre 1
TIPOSERVICO      = "99"     # Tipo de serviço — 99 (Outros Pag.)

# =============================================================================
# PARÂMETROS DA ROTINA 749
# Extraídos diretamente do tracer (INSERT INTO PCLANC)
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
    # DUPLIC é dinâmico: igual ao número da parcela (1, 2, ...)
    # Não use este valor fixo — inserir_lancamento passa str(parcela)
    "CODROTINAALT":        "A",   # Confirmado no tracer
}
