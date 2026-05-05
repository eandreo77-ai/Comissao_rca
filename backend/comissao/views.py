"""
Views (API) para Comissão RCA.

Endpoints:
  POST   /api/upload/          - Upload do Excel
  GET    /api/importacoes/     - Lista importações
  GET    /api/importacoes/:id/ - Detalhe com itens
  POST   /api/validar/:id/     - Validar itens no Oracle
  POST   /api/gravar/:id/      - Gravar itens validados na PCLANC
  DELETE /api/importacoes/:id/ - Cancelar importação
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import ImportacaoComissao, ItemComissao
from .serializers import (
    ImportacaoComissaoSerializer,
    ImportacaoListSerializer,
    UploadExcelSerializer,
)
from .services import parse_excel, validar_item_oracle, gravar_pclanc


@api_view(['POST'])
def upload_excel(request):
    """Upload e parse da planilha Excel."""
    serializer = UploadExcelSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    arquivo = serializer.validated_data['arquivo']
    dt_referencia = serializer.validated_data['dt_referencia']

    # Valida extensão
    if not arquivo.name.endswith(('.xlsx', '.xls')):
        return Response(
            {'erro': 'Arquivo deve ser Excel (.xlsx ou .xls)'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # Cria o registro da importação
    importacao = ImportacaoComissao.objects.create(
        arquivo_nome=arquivo.name,
        arquivo=arquivo,
        dt_referencia=dt_referencia,
        usuario=request.user.username if request.user.is_authenticated else 'admin',
    )

    try:
        resultado = parse_excel(importacao)
    except Exception as e:
        importacao.status = 'E'
        importacao.observacao = f'Erro ao processar planilha: {str(e)}'
        importacao.save()
        return Response(
            {'erro': str(e), 'importacao_id': importacao.id},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({
        'importacao_id': importacao.id,
        'arquivo': arquivo.name,
        'resultado': resultado,
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def listar_importacoes(request):
    """Lista todas as importações."""
    importacoes = ImportacaoComissao.objects.all()
    serializer = ImportacaoListSerializer(importacoes, many=True)
    return Response(serializer.data)


@api_view(['GET', 'DELETE'])
def detalhe_importacao(request, pk):
    """Detalhe de uma importação com seus itens."""
    try:
        importacao = ImportacaoComissao.objects.get(pk=pk)
    except ImportacaoComissao.DoesNotExist:
        return Response(
            {'erro': 'Importação não encontrada'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if request.method == 'DELETE':
        if importacao.status == 'G':
            return Response(
                {'erro': 'Não é possível cancelar importação já gravada no banco'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        importacao.status = 'C'
        importacao.save()
        return Response({'mensagem': 'Importação cancelada'})

    serializer = ImportacaoComissaoSerializer(importacao)
    return Response(serializer.data)


@api_view(['POST'])
def validar_importacao(request, pk):
    """Valida todos os itens pendentes contra o Oracle."""
    try:
        importacao = ImportacaoComissao.objects.get(pk=pk)
    except ImportacaoComissao.DoesNotExist:
        return Response(
            {'erro': 'Importação não encontrada'},
            status=status.HTTP_404_NOT_FOUND,
        )

    itens = importacao.itens.filter(status='P')
    validados = 0
    erros = 0

    for item in itens:
        if validar_item_oracle(item):
            validados += 1
        else:
            erros += 1

    # Atualiza status da importação
    total_erros = importacao.itens.filter(status='E').count()
    importacao.total_erros = total_erros
    importacao.status = 'V' if total_erros == 0 else 'E'
    importacao.save()

    return Response({
        'validados': validados,
        'erros': erros,
        'total_erros': total_erros,
    })


@api_view(['POST'])
def gravar_importacao(request, pk):
    """Grava todos os itens validados na PCLANC."""
    try:
        importacao = ImportacaoComissao.objects.get(pk=pk)
    except ImportacaoComissao.DoesNotExist:
        return Response(
            {'erro': 'Importação não encontrada'},
            status=status.HTTP_404_NOT_FOUND,
        )

    if importacao.status not in ('V', 'E'):
        return Response(
            {'erro': f'Importação com status "{importacao.get_status_display()}" não pode ser gravada'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    itens = importacao.itens.filter(status='V')
    gravados = 0
    erros = 0

    for item in itens:
        try:
            if gravar_pclanc(item):
                gravados += 1
            else:
                erros += 1
        except Exception as e:
            item.status = 'E'
            item.erro_msg = f'Erro ao gravar: {str(e)}'
            item.save()
            erros += 1

    # Atualiza status
    if gravados > 0 and erros == 0:
        importacao.status = 'G'
    importacao.save()

    return Response({
        'gravados': gravados,
        'erros': erros,
    })
