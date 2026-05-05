"""URLs da API de Comissão RCA."""
from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_excel, name='upload-excel'),
    path('importacoes/', views.listar_importacoes, name='listar-importacoes'),
    path('importacoes/<int:pk>/', views.detalhe_importacao, name='detalhe-importacao'),
    path('validar/<int:pk>/', views.validar_importacao, name='validar-importacao'),
    path('gravar/<int:pk>/', views.gravar_importacao, name='gravar-importacao'),
]
