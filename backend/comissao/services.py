"""
Serviços de negócio para Comissão RCA.

- parse_excel: Lê a planilha e cria os itens no banco local (SQLite)
- validar_itens: Valida os dados contra o Oracle (PCUSUARI, PCFILIAL, PCCONTA)
- gravar_pclanc: Grava os itens validados na PCLANC (Oracle)
"""
import openpyxl
from datetime import datetime
from decimal import Decimal, InvalidOperation
from django.conf import settings


def parse_excel(importacao):
    """
    Lê o arquivo Excel e cria os ItemComissao no banco local.

    Colunas esperadas na planilha:
    A: CODUSUR (int)
    B: NOME_RCA (str, opcional)
    C: CODFILIAL (str)
    D: VALOR (decimal)
    E: CODCONTA (int)
    F: DTLANC (date)
    G: DTVENC (date)
    H: HISTORICO (str, opcional)
    """
    from .models import ItemComissao

    wb = openpyxl.load_workbook(importacao.arquivo.path, read_only=True, data_only=True)
    ws = wb.active

    itens_criados = []
    erros = 0
    total_valor = Decimal('0')

    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        # Pula linhas completamente vazias
        if not row or all(cell is None for cell in row):
            continue

        erro_msg = []

        # ---- CODUSUR ----
        codusur = row[0] if len(row) > 0 else None
        if codusur is None:
            erro_msg.append('CODUSUR é obrigatório')
        else:
            try:
                codusur = int(codusur)
            except (ValueError, TypeError):
                erro_msg.append(f'CODUSUR inválido: {codusur}')
                codusur = 0

        # ---- NOME_RCA (opcional) ----
        nome_rca = str(row[1]).strip() if len(row) > 1 and row[1] else ''

        # ---- CODFILIAL ----
        codfilial = row[2] if len(row) > 2 else None
        if codfilial is None:
            erro_msg.append('CODFILIAL é obrigatório')
        else:
            codfilial = str(codfilial).strip()

        # ---- VALOR ----
        valor = row[3] if len(row) > 3 else None
        if valor is None:
            erro_msg.append('VALOR é obrigatório')
            valor = Decimal('0')
        else:
            try:
                if isinstance(valor, str):
                    valor = valor.replace('.', '').replace(',', '.')
                valor = Decimal(str(valor))
                if valor <= 0:
                    erro_msg.append(f'VALOR deve ser positivo: {valor}')
            except (InvalidOperation, ValueError, TypeError):
                erro_msg.append(f'VALOR inválido: {valor}')
                valor = Decimal('0')

        # ---- CODCONTA ----
        codconta = row[4] if len(row) > 4 else None
        if codconta is None:
            erro_msg.append('CODCONTA é obrigatório')
            codconta = 0
        else:
            try:
                codconta = int(codconta)
            except (ValueError, TypeError):
                erro_msg.append(f'CODCONTA inválido: {codconta}')
                codconta = 0

        # ---- DTLANC ----
        dtlanc = row[5] if len(row) > 5 else None
        if dtlanc is None:
            erro_msg.append('DTLANC é obrigatório')
        elif isinstance(dtlanc, str):
            try:
                dtlanc = datetime.strptime(dtlanc.strip(), '%d/%m/%Y').date()
            except ValueError:
                erro_msg.append(f'DTLANC formato inválido (use DD/MM/YYYY): {dtlanc}')
                dtlanc = None
        elif isinstance(dtlanc, datetime):
            dtlanc = dtlanc.date()

        # ---- DTVENC ----
        dtvenc = row[6] if len(row) > 6 else None
        if dtvenc is None:
            erro_msg.append('DTVENC é obrigatório')
        elif isinstance(dtvenc, str):
            try:
                dtvenc = datetime.strptime(dtvenc.strip(), '%d/%m/%Y').date()
            except ValueError:
                erro_msg.append(f'DTVENC formato inválido (use DD/MM/YYYY): {dtvenc}')
                dtvenc = None
        elif isinstance(dtvenc, datetime):
            dtvenc = dtvenc.date()

        # ---- HISTORICO (opcional) ----
        historico = str(row[7]).strip() if len(row) > 7 and row[7] else f'Comissão {importacao.dt_referencia}'

        # Determina status da linha
        status = 'E' if erro_msg else 'P'
        if erro_msg:
            erros += 1

        total_valor += valor if valor else Decimal('0')

        item = ItemComissao(
            importacao=importacao,
            linha_excel=row_num,
            codusur=codusur or 0,
            nome_rca=nome_rca,
            codfilial=codfilial or '',
            valor=valor,
            codconta=codconta,
            dtlanc=dtlanc,
            dtvenc=dtvenc,
            historico=historico,
            status=status,
            erro_msg='; '.join(erro_msg) if erro_msg else None,
        )
        itens_criados.append(item)

    wb.close()

    # Bulk create para performance
    ItemComissao.objects.bulk_create(itens_criados)

    # Atualiza totais na importação
    importacao.total_linhas = len(itens_criados)
    importacao.total_valor = total_valor
    importacao.total_erros = erros
    importacao.status = 'E' if erros > 0 else 'V'
    importacao.save()

    return {
        'total_linhas': len(itens_criados),
        'total_valor': float(total_valor),
        'total_erros': erros,
    }


def validar_item_oracle(item):
    """
    Valida um item contra o banco Oracle.
    Verifica se CODUSUR existe na PCUSUARI, filial na PCFILIAL, conta na PCCONTA.

    TODO: Implementar quando conectar no Oracle.
    Por enquanto retorna sempre válido para testes com SQLite.
    """
    # Simulação para dev local
    item.nome_rca_banco = item.nome_rca or f'RCA {item.codusur}'
    item.tipopessoa = 'F'
    item.status = 'V'
    item.erro_msg = None
    item.save()
    return True


def gravar_pclanc(item):
    """
    Grava um item validado na PCLANC do Oracle.
    Segue exatamente o fluxo da rotina 749:

    1. Obtém PROXNUMLANC de PCCONSUM (FOR UPDATE)
    2. Incrementa PROXNUMLANC
    3. INSERT na PCLANC
    4. COMMIT

    TODO: Implementar quando conectar no Oracle.
    """
    config = settings.COMISSAO_CONFIG

    # SQL que será executado no Oracle (referência do tracer):
    #
    # SELECT NVL(PROXNUMLANC,1) PROXNUMLANC FROM PCCONSUM FOR UPDATE
    # UPDATE PCCONSUM SET PROXNUMLANC = NVL(PROXNUMLANC,1) + 1
    #
    # INSERT INTO PCLANC (
    #     RECNUM, DTLANC, HISTORICO, DUPLIC, CODFILIAL, INDICE,
    #     TIPOLANC, TIPOPARCEIRO, NOMEFUNC, MOEDA, NFSERVICO,
    #     BOLETO, UTILIZOURATEIOCONTA, PRCRATEIOUTILIZADO,
    #     VALOR, CODCONTA, RECNUMPRINC, DTVENC, DTEMISSAO,
    #     DTCOMPETENCIA, FORNECEDOR, CODROTINACAD, CODROTINAALT,
    #     PARCELA, NUMNOTA, CODFORNEC, ...
    # ) VALUES (
    #     :recnum, :dtlanc, :historico, '1', :codfilial, 'A',
    #     'C', 'R', 'IMPORTACAO COMISSAO', '1', 'N',
    #     'N', 'N', 100,
    #     :valor, :codconta, :recnum, :dtvenc, :dtlanc,
    #     :dtcompetencia, :nome_rca, 749, 'A',
    #     '1', :codfornec, :codusur, ...
    # )

    # Simulação para dev local
    from django.utils import timezone
    item.recnum = item.id + 7000000  # Simula RECNUM
    item.dt_gravacao = timezone.now()
    item.status = 'G'
    item.save()
    return True
