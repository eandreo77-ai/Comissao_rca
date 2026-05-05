"""Serializers para a API de Comissão RCA."""
from rest_framework import serializers
from .models import ImportacaoComissao, ItemComissao


class ItemComissaoSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ItemComissao
        fields = [
            'id', 'linha_excel', 'codusur', 'nome_rca', 'codfilial',
            'valor', 'codconta', 'dtlanc', 'dtvenc', 'historico',
            'status', 'status_display', 'erro_msg',
            'nome_rca_banco', 'tipopessoa', 'recnum', 'dt_gravacao',
        ]


class ImportacaoComissaoSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    itens = ItemComissaoSerializer(many=True, read_only=True)

    class Meta:
        model = ImportacaoComissao
        fields = [
            'id', 'arquivo_nome', 'arquivo', 'dt_importacao',
            'dt_referencia', 'usuario', 'status', 'status_display',
            'total_linhas', 'total_valor', 'total_erros', 'observacao',
            'itens',
        ]


class ImportacaoListSerializer(serializers.ModelSerializer):
    """Serializer resumido para listagem (sem itens)."""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = ImportacaoComissao
        fields = [
            'id', 'arquivo_nome', 'dt_importacao', 'dt_referencia',
            'usuario', 'status', 'status_display',
            'total_linhas', 'total_valor', 'total_erros',
        ]


class UploadExcelSerializer(serializers.Serializer):
    """Serializer para o upload do Excel."""
    arquivo = serializers.FileField()
    dt_referencia = serializers.CharField(max_length=7, help_text='Formato: MM/YYYY')
