"""
Módulo de conexão e operações com Oracle para o sistema de comissões RCA.
Baseado no tracer da rotina 749 do WinThor.
"""
import oracledb
import unicodedata
from datetime import date, datetime
from typing import Optional, Dict, List, Tuple
from config import ORACLE_CONFIG, ROTINA_749, CODCONTA_PADRAO, CODFILIAL_PADRAO, TIPOSERVICO, INSTANTCLIENT_PATH

def _historico_limpo(texto: str) -> str:
    """Converte para maiúsculo e remove acentos (padrão legível no WinThor)."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return sem_acento.upper()


# ── Modo grosso (thick mode) — obrigatório para Oracle 11g ──────────────────
# init_oracle_client deve ser chamado uma única vez antes de qualquer conexão
try:
    oracledb.init_oracle_client(lib_dir=INSTANTCLIENT_PATH)
except Exception:
    pass  # já foi inicializado em chamada anterior (módulo recarregado)
# ────────────────────────────────────────────────────────────────────────────


class OracleConnection:
    """Gerencia conexão com o banco Oracle"""

    def __init__(self):
        self.connection = None

    def conectar(self) -> bool:
        """Estabelece conexão com o Oracle (modo grosso, Oracle 11g)"""
        try:
            self.connection = oracledb.connect(
                user=ORACLE_CONFIG["user"],
                password=ORACLE_CONFIG["password"],
                dsn=ORACLE_CONFIG["dsn"],
                tcp_connect_timeout=10,
            )
            # NLS idêntico ao que a rotina 749 configura na sessão
            cursor = self.connection.cursor()
            cursor.execute("ALTER SESSION SET NLS_DATE_FORMAT='DD/MM/YYYY'")
            cursor.execute("ALTER SESSION SET NLS_NUMERIC_CHARACTERS='.,'")
            cursor.close()
            return True
        except Exception as e:
            print(f"Erro ao conectar no Oracle: {e}")
            return False

    def desconectar(self):
        """Fecha a conexão"""
        if self.connection:
            try:
                self.connection.close()
            except Exception:
                pass
            self.connection = None

    def get_cursor(self):
        """Retorna um cursor ativo"""
        if not self.connection:
            self.conectar()
        return self.connection.cursor()


class ValidadorRCA:
    """Valida dados dos RCAs contra as tabelas do WinThor"""

    def __init__(self, db: OracleConnection):
        self.db = db

    def validar_rca(self, codusur: int) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Valida se o RCA existe na PCUSUARI (mesma query do tracer 749).
        Retorna: (existe, nome_rca, tipo_pessoa)
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute("""
                SELECT NOME AS PARCEIRO,
                       NVL(TIPOPESSOA,'J') AS TIPOPESSOA
                  FROM PCUSUARI
                 WHERE NOME IS NOT NULL
                   AND PCUSUARI.DTTERMINO IS NULL
                   AND CODUSUR = :COD
            """, {"COD": str(codusur)})
            row = cursor.fetchone()
            cursor.close()
            if row:
                return True, row[0], row[1]
            return False, None, None
        except Exception as e:
            return False, None, str(e)

    def validar_conta(self, codconta: int, codfunc: int = 2245) -> Tuple[bool, Optional[str]]:
        """
        Valida se a conta contábil existe na PCCONTA (baseado no tracer 749).
        Retorna: (existe, tipo_conta)
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute("""
                SELECT PCCONTA.CODCONTA, PCCONTA.CONTA, PCCONTA.TIPO
                FROM PCCONTA
                WHERE PCCONTA.CODCONTA = :CODCONTA
                  AND PCCONTA.TIPO <> 'I'
            """, {"CODCONTA": str(codconta)})
            row = cursor.fetchone()
            cursor.close()
            if row:
                return True, row[2]
            return False, None
        except Exception as e:
            return False, str(e)

    def validar_filial(self, codfilial: str) -> Tuple[bool, Optional[str]]:
        """
        Valida se a filial existe na PCFILIAL.
        Retorna: (existe, razao_social)
        """
        try:
            cursor = self.db.get_cursor()
            cursor.execute("""
                SELECT CODIGO, RAZAOSOCIAL
                FROM PCFILIAL
                WHERE CODIGO = :CODFILIAL
                  AND DTEXCLUSAO IS NULL
            """, {"CODFILIAL": codfilial})
            row = cursor.fetchone()
            cursor.close()
            if row:
                return True, row[1]
            return False, None
        except Exception as e:
            return False, str(e)

    def listar_filiais(self) -> List[Dict]:
        """Retorna lista de filiais ativas"""
        try:
            cursor = self.db.get_cursor()
            cursor.execute("""
                SELECT CODIGO, RAZAOSOCIAL
                FROM PCFILIAL
                WHERE CODIGO <> '99'
                  AND DTEXCLUSAO IS NULL
                ORDER BY CODIGO
            """)
            rows = cursor.fetchall()
            cursor.close()
            return [{"codigo": r[0], "razaosocial": r[1]} for r in rows]
        except Exception:
            return []

    def listar_contas(self) -> List[Dict]:
        """Retorna lista de contas contábeis disponíveis para lançamento"""
        try:
            cursor = self.db.get_cursor()
            cursor.execute("""
                SELECT PCCONTA.CODCONTA, PCCONTA.CONTA, PCCONTA.TIPO
                FROM PCCONTA, PCGRUPO
                WHERE PCCONTA.GRUPOCONTA = PCGRUPO.CODGRUPO
                  AND PCGRUPO.CODGRUPO >= 100
                  AND PCCONTA.TIPO <> 'I'
                ORDER BY PCCONTA.CODCONTA
            """)
            rows = cursor.fetchall()
            cursor.close()
            return [{"codconta": r[0], "conta": r[1], "tipo": r[2]} for r in rows]
        except Exception:
            return []


class GravadorPCLANC:
    """
    Grava lançamentos na PCLANC conforme o padrão da rotina 749.
    Baseado integralmente no INSERT capturado no tracer.
    """

    def __init__(self, db: OracleConnection):
        self.db = db

    def obter_proximo_recnum(self) -> int:
        """
        Obtém o próximo RECNUM usando PCCONSUM.PROXNUMLANC com FOR UPDATE
        (exatamente como a rotina 749 faz no tracer).
        """
        cursor = self.db.get_cursor()
        cursor.execute("SELECT NVL(PROXNUMLANC,1) PROXNUMLANC FROM PCCONSUM FOR UPDATE WAIT 10")
        row = cursor.fetchone()
        recnum = int(row[0])
        cursor.execute("UPDATE PCCONSUM SET PROXNUMLANC = NVL(PROXNUMLANC,1) + 1")
        self.db.connection.commit()
        cursor.close()
        return recnum

    def _executar_insert(self, cursor, recnum: int, lanc: Dict) -> None:
        """Executa o INSERT na PCLANC sem commit — usado por inserir_lote."""
        cfg = ROTINA_749
        cursor.execute("""
            INSERT INTO PCLANC (
                RECNUM, RECNUMPRINC,
                DTLANC, DTEMISSAO, DTCOMPETENCIA,
                CODFILIAL, TIPOLANC, INDICE, MOEDA,
                CODCONTA, HISTORICO, HISTORICO2, TIPOPARCEIRO,
                CODFORNEC, DTVENC, VALOR,
                NFSERVICO, CODROTINACAD, PARCELA, NUMNOTA,
                UTILIZOURATEIOCONTA, PRCRATEIOUTILIZADO,
                FORNECEDOR, REINFEVENTOR4040, NOMEFUNC,
                VLRUTILIZADOADIANTFORNEC,
                DUPLIC, CODROTINAALT, TIPOSERVICO,
                AGENDAMENTO, LACREDIGCONECSOCIAL, OPCAOPAGAMENTOIPVA
            ) VALUES (
                :RECNUM, :RECNUMPRINC,
                TRUNC(SYSDATE), TRUNC(SYSDATE), TRUNC(SYSDATE),
                :CODFILIAL, :TIPOLANC, :INDICE, :MOEDA,
                :CODCONTA, :HISTORICO, :HISTORICO2, :TIPOPARCEIRO,
                :CODFORNEC, :DTVENC, :VALOR,
                :NFSERVICO, :CODROTINACAD, :PARCELA, :NUMNOTA,
                :UTILIZOURATEIOCONTA, :PRCRATEIOUTILIZADO,
                :FORNECEDOR, :REINFEVENTOR4040, :NOMEFUNC,
                :VLRUTILIZADOADIANTFORNEC,
                :DUPLIC, :CODROTINAALT, :TIPOSERVICO,
                NULL, :LACREDIGCONECSOCIAL, :OPCAOPAGAMENTOIPVA
            )
        """, {
            "RECNUM":                   recnum,
            "RECNUMPRINC":              recnum,
            "CODFILIAL":                lanc["codfilial"],
            "TIPOLANC":                 cfg["TIPOLANC"],
            "INDICE":                   cfg["INDICE"],
            "MOEDA":                    cfg["MOEDA"],
            "CODCONTA":                 lanc["codconta"],
            "HISTORICO":                _historico_limpo(lanc["historico"]),
            "HISTORICO2":               f"(Parcela: {lanc['parcela']})",
            "TIPOPARCEIRO":             cfg["TIPOPARCEIRO"],
            "CODFORNEC":                lanc["codusur"],
            "DTVENC":                   lanc["dtvenc"],
            "VALOR":                    lanc["valor"],
            "NFSERVICO":                cfg["NFSERVICO"],
            "CODROTINACAD":             cfg["CODROTINACAD"],
            "PARCELA":                  str(lanc["parcela"]),
            "NUMNOTA":                  0,
            "UTILIZOURATEIOCONTA":      cfg["UTILIZOURATEIOCONTA"],
            "PRCRATEIOUTILIZADO":       cfg["PRCRATEIOUTILIZADO"],
            "FORNECEDOR":               lanc["nome_rca"],
            "REINFEVENTOR4040":         cfg["REINFEVENTOR4040"],
            "NOMEFUNC":                 "IMPORTACAO WEB",
            "VLRUTILIZADOADIANTFORNEC": 0,
            "DUPLIC":                   str(lanc["parcela"]),
            "LACREDIGCONECSOCIAL":      0,
            "OPCAOPAGAMENTOIPVA":       0,
            "CODROTINAALT":             cfg["CODROTINAALT"],
            "TIPOSERVICO":              TIPOSERVICO,
        })

    def inserir_lancamento(
        self,
        codusur: int,
        nome_rca: str,
        valor: float,
        codconta: int,
        codfilial: str,
        historico: str = "COMISSAO RCA",
        dtvenc: Optional[date] = None,
        parcela: int = 1,
    ) -> int:
        """Insere um único lançamento na PCLANC e retorna o RECNUM gerado."""
        recnum = self.obter_proximo_recnum()
        lanc = {
            "codusur": codusur, "nome_rca": nome_rca, "valor": valor,
            "codconta": codconta, "codfilial": codfilial, "historico": historico,
            "dtvenc": dtvenc, "parcela": parcela,
        }
        cursor = self.db.get_cursor()
        self._executar_insert(cursor, recnum, lanc)
        self.db.connection.commit()
        cursor.close()
        return recnum

    def inserir_lote(self, lancamentos: List[Dict]) -> Tuple[bool, List[int], Optional[str]]:
        """
        Insere um lote de lançamentos na PCLANC em transação única.
        RECNUMs são pré-alocados (cada um faz commit do PCCONSUM para liberar o lock).
        Todos os INSERTs na PCLANC são commitados juntos — em caso de erro, há rollback completo.
        Retorna: (sucesso, lista_recnums, erro)
        """
        recnums = []
        cursor = None
        try:
            # Pré-alocar todos os RECNUMs antes de abrir a transação dos INSERTs
            for _ in lancamentos:
                recnums.append(self.obter_proximo_recnum())

            # Inserir todos sem commit intermediário
            cursor = self.db.get_cursor()
            for recnum, lanc in zip(recnums, lancamentos):
                self._executar_insert(cursor, recnum, lanc)

            # Commit único de todos os INSERTs
            self.db.connection.commit()
            cursor.close()
            return True, recnums, None

        except Exception as e:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass
            try:
                self.db.connection.rollback()
            except Exception:
                pass
            return False, recnums, str(e)

    def verificar_duplicatas(self, lancamentos: List[Dict]) -> List[Dict]:
        """
        Verifica se algum lançamento já existe na PCLANC hoje
        (mesmo CODFORNEC + DTVENC + VALOR + HISTORICO gravado em TRUNC(SYSDATE)).
        Retorna lista de lançamentos que parecem duplicados.
        """
        duplicatas = []
        try:
            cursor = self.db.get_cursor()
            for lanc in lancamentos:
                cursor.execute("""
                    SELECT COUNT(*) FROM PCLANC
                     WHERE CODFORNEC        = :CODUSUR
                       AND DTVENC           = :DTVENC
                       AND VALOR            = :VALOR
                       AND HISTORICO        = :HISTORICO
                       AND TRUNC(DTLANC)    = TRUNC(SYSDATE)
                """, {
                    "CODUSUR":   lanc["codusur"],
                    "DTVENC":    lanc["dtvenc"],
                    "VALOR":     lanc["valor"],
                    "HISTORICO": _historico_limpo(lanc.get("historico", "")),
                })
                if cursor.fetchone()[0] > 0:
                    duplicatas.append(lanc)
            cursor.close()
        except Exception:
            pass
        return duplicatas


def testar_conexao() -> Tuple[bool, str]:
    """Testa a conexão com o Oracle e retorna status"""
    db = OracleConnection()
    try:
        if db.conectar():
            cursor = db.get_cursor()
            cursor.execute("SELECT SYSDATE, EMPRESA FROM PCCONSUM")
            row = cursor.fetchone()
            cursor.close()
            db.desconectar()
            return True, f"Conectado! Empresa: {row[1]} | Data servidor: {row[0]}"
        return False, "Falha na conexão"
    except Exception as e:
        db.desconectar()
        return False, str(e)
