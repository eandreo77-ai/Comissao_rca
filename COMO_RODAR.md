# Comissão RCA - Como Rodar Localmente

## Estrutura do Projeto

```
Comissao_RCA/
├── backend/          # Django + DRF (API REST)
│   ├── config/       # Configurações Django
│   ├── comissao/     # App principal (models, views, services)
│   ├── manage.py
│   └── requirements.txt
├── frontend/         # React + Vite
│   ├── src/
│   │   ├── pages/    # UploadPage, ImportacoesPage, DetalhePage
│   │   ├── services/ # API client (axios)
│   │   └── App.jsx
│   └── package.json
└── COMO_RODAR.md
```

## 1. Backend (Django)

```bash
cd backend

# Criar e ativar ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux

# Instalar dependencias
pip install -r requirements.txt

# Criar banco SQLite e tabelas
python manage.py makemigrations comissao
python manage.py migrate

# Criar superusuario (opcional, para acessar /admin)
python manage.py createsuperuser

# Rodar servidor
python manage.py runserver
```

Backend rodando em: http://localhost:8000

API disponivel:
- POST   /api/upload/          → Upload do Excel
- GET    /api/importacoes/     → Lista importacoes
- GET    /api/importacoes/:id/ → Detalhe com itens
- POST   /api/validar/:id/     → Validar itens
- POST   /api/gravar/:id/      → Gravar na PCLANC
- DELETE /api/importacoes/:id/ → Cancelar importacao

## 2. Frontend (React)

```bash
cd frontend

# Instalar dependencias
npm install

# Rodar dev server
npm run dev
```

Frontend rodando em: http://localhost:5173

O Vite faz proxy automatico de /api para o Django (porta 8000).

## 3. Fluxo de Uso

1. Abrir http://localhost:5173
2. Selecionar mes de referencia
3. Arrastar ou selecionar planilha Excel
4. Clicar "Importar Planilha"
5. Revisar dados na tela de detalhe
6. Clicar "Validar" (checa dados contra o banco)
7. Clicar "Gravar no Contas a Pagar" (INSERT na PCLANC)

## 4. Formato da Planilha Excel

| Coluna | Campo      | Tipo    | Obrigatorio | Exemplo           |
|--------|------------|---------|-------------|-------------------|
| A      | CODUSUR    | Numero  | Sim         | 11                |
| B      | NOME_RCA   | Texto   | Nao         | TELMI TEIXEIRA    |
| C      | CODFILIAL  | Texto   | Sim         | 1                 |
| D      | VALOR      | Decimal | Sim         | 7219.48           |
| E      | CODCONTA   | Numero  | Sim         | 100010            |
| F      | DTLANC     | Data    | Sim         | 07/04/2026        |
| G      | DTVENC     | Data    | Sim         | 08/04/2026        |
| H      | HISTORICO  | Texto   | Nao         | Comissao Mar/2026 |

Primeira linha = cabecalhos. Dados a partir da linha 2.

## 5. Proximos Passos

- [ ] Conectar no Oracle (BDTESTE) para validacao real
- [ ] Implementar INSERT real na PCLANC
- [ ] Adicionar autenticacao de usuario
- [ ] Dockerizar para deploy no servidor Ubuntu
- [ ] Configurar Nginx como reverse proxy
