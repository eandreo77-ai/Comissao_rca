"""Admin para Comissão RCA."""
from django.contrib import admin
from .models import ImportacaoComissao, ItemComissao


class ItemComissaoInline(admin.TabularInline):
    model = ItemComissao
    extra = 0
    readonly_fields = ['linha_excel', 'codusur', 'nome_rca', 'valor', 'status', 'erro_msg', 'recnum']


@admin.register(ImportacaoComissao)
class ImportacaoComissaoAdmin(admin.ModelAdmin):
    list_display = ['id', 'arquivo_nome', 'dt_referencia', 'status', 'total_linhas', 'total_valor', 'dt_importacao']
    list_filter = ['status', 'dt_referencia']
    inlines = [ItemComissaoInline]


@admin.register(ItemComissao)
class ItemComissaoAdmin(admin.ModelAdmin):
    list_display = ['id', 'importacao', 'linha_excel', 'codusur', 'nome_rca', 'valor', 'status', 'recnum']
    list_filter = ['status']
    search_fields = ['codusur', 'nome_rca']
