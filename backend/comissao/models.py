"""
Models para importação de comissão de RCA.

ImportacaoComissao - Registro de cada arquivo importado
ItemComissao - Cada linha da planilha (cada RCA/valor)
"""
from django.db import models


class ImportacaoComissao(models.Model):
    """Registro de cada importação de planilha."""

    STATUS_CHOICES = [
        ('P', 'Pendente Validação'),
        ('V', 'Validado'),
        ('E', 'Com Erros'),
        ('G', 'Gravado no Banco'),
        ('C', 'Cancelado'),
    ]

    arquivo_nome = models.CharField('Nome do Arquivo', max_length=255)
    arquivo = models.FileField('Arquivo Excel', upload_to='uploads/%Y/%m/')
    dt_importacao = models.DateTimeField('Data Importação', auto_now_add=True)
    dt_referencia = models.CharField('Mês Referência', max_length=7, help_text='Formato: MM/YYYY')
    usuario = models.CharField('Usuário', max_length=100, default='admin')
    status = models.CharField('Status', max_length=1, choices=STATUS_CHOICES, default='P')
    total_linhas = models.IntegerField('Total Linhas', default=0)
    total_valor = models.DecimalField('Valor Total', max_digits=15, decimal_places=2, default=0)
    total_erros = models.IntegerField('Total Erros', default=0)
    observacao = models.TextField('Observação', blank=True, null=True)

    class Meta:
        db_table = 'importacao_comissao'
        ordering = ['-dt_importacao']
        verbose_name = 'Importação de Comissão'
        verbose_name_plural = 'Importações de Comissão'

    def __str__(self):
        return f'{self.arquivo_nome} - {self.dt_referencia} ({self.get_status_display()})'


class ItemComissao(models.Model):
    """Cada linha da planilha importada."""

    STATUS_CHOICES = [
        ('P', 'Pendente'),
        ('V', 'Validado'),
        ('E', 'Com Erro'),
        ('G', 'Gravado'),
    ]

    importacao = models.ForeignKey(
        ImportacaoComissao,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name='Importação',
    )
    linha_excel = models.IntegerField('Linha no Excel')

    # Campos da planilha (dados do RCA)
    codusur = models.IntegerField('Cód. RCA (CODUSUR)')
    nome_rca = models.CharField('Nome RCA', max_length=200, blank=True, null=True)
    codfilial = models.CharField('Cód. Filial', max_length=4)
    valor = models.DecimalField('Valor Comissão', max_digits=15, decimal_places=2)
    codconta = models.IntegerField('Cód. Conta')
    dtlanc = models.DateField('Data Lançamento')
    dtvenc = models.DateField('Data Vencimento')
    historico = models.CharField('Histórico', max_length=200, blank=True, null=True)

    # Campos de validação
    status = models.CharField('Status', max_length=1, choices=STATUS_CHOICES, default='P')
    erro_msg = models.TextField('Mensagem de Erro', blank=True, null=True)

    # Campos preenchidos após validação no Oracle
    nome_rca_banco = models.CharField('Nome RCA (Banco)', max_length=200, blank=True, null=True)
    tipopessoa = models.CharField('Tipo Pessoa', max_length=1, blank=True, null=True)

    # Campos após gravação no contas a pagar
    recnum = models.BigIntegerField('RECNUM (PCLANC)', blank=True, null=True)
    dt_gravacao = models.DateTimeField('Data Gravação', blank=True, null=True)

    class Meta:
        db_table = 'item_comissao'
        ordering = ['linha_excel']
        verbose_name = 'Item de Comissão'
        verbose_name_plural = 'Itens de Comissão'

    def __str__(self):
        return f'Linha {self.linha_excel} - RCA {self.codusur} - R$ {self.valor}'
