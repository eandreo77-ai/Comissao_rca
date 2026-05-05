# Documentação — Sistema de Importação de Comissões RCA
**Rotina 749 | WinThor | ROFE**

---

## Sumário

1. [Visão Geral](#1-visão-geral)
2. [Arquitetura](#2-arquitetura)
3. [Estrutura de Arquivos](#3-estrutura-de-arquivos)
4. [Pré-requisitos e Instalação](#4-pré-requisitos-e-instalação)
5. [Configuração](#5-configuração)
6. [Como Executar](#6-como-executar)
7. [Fluxo de Uso](#7-fluxo-de-uso)
8. [Formato da Planilha Excel](#8-formato-da-planilha-excel)
9. [Módulos do Sistema](#9-módulos-do-sistema)
10. [Banco de Dados — Tabelas Envolvidas](#10-banco-de-dados--tabelas-envolvidas)
11. [Regras de Negócio](#11-regras-de-negócio)
12. [Alertas e Validações](#12-alertas-e-validações)
13. [Histórico da Sessão](#13-histórico-da-sessão)
14. [Troubleshooting](#14-troubleshooting)

---

## 1. Visão Geral

Sistema web para importação em lote de comissões de RCAs (Representantes Comerciais) diretamente no módulo **Contas a Pagar** do WinThor, tabela **PCLANC**, replicando o comportamento da **Rotina 749** (Inclusão de Lançamentos no Contas a Pagar).

O usuário preenche uma planilha Excel com os dados dos RCAs e valores por parcela, faz o upload no sistema, confere os dados na tela e clica em **Executar Gravação**. O sistema insere os registros no Oracle sem necessidade de digitação manual no WinThor.

**Tecnologias:**
- Interface: **Streamlit** (Python)
- Banco de dados: **Oracle 11g** via `python-oracledb` em modo grosso (thick mode)
- Planilha: **openpyxl**

---

## 2. Arquitetura

```
┌─────────────────────────────────────────────┐
│              Usuário (navegador)            │
│         http://localhost:8501               │
└────────────────────┬────────────────────────┘
                     │
┌────────────────────▼────────────────────────┐
│           app.py  (Streamlit)               │
│  ┌──────────────┐  ┌───────────────────┐    │
│  │ excel_parser │  │    oracle_db      │    │
│  │ ler_excel()  │  │ OracleConnection  │    │
│  └──────────────┘  │ ValidadorRCA      │    │
│                    │ GravadorPCLANC    │    │
│  ┌──────────────┐  └────────┬──────────┘    │
│  │   models.py  │           │               │
│  │ ComissaoRCA  │           │               │
│  └──────────────┘           │               │
└────────────────────────┬────┘               
                         │
┌────────────────────────▼────────────────────┐
│         Oracle 11g — WinThor                │
│  PCLANC  │  PCUSUARI  │  PCCONSUM           │
└─────────────────────────────────────────────┘
```

---

## 3. Estrutura de Arquivos

```
Comissao_RCA/
├── app/
│   ├── app.py            # Interface Streamlit (ponto de entrada)
│   ├── config.py         # Configurações: Oracle, valores fixos, parâmetros rotina 749
│   ├── oracle_db.py      # Conexão Oracle, validações, INSERT na PCLANC
│   ├── excel_parser.py   # Leitura e parse da planilha Excel
│   ├── models.py         # Modelos Pydantic (ComissaoRCA, etc.)
│   └── requirements.txt  # Dependências Python
├── tracer 749.log        # Log do tracer WinThor (referência do INSERT)
└── DOCUMENTACAO.md       # Este arquivo
```

---

## 4. Pré-requisitos e Instalação

### 4.1 Python
- Python 3.10 ou superior

### 4.2 Oracle Instant Client (obrigatório para Oracle 11g)
O driver `python-oracledb` em modo grosso exige o Oracle Instant Client instalado na máquina.

1. Baixar: [Oracle Instant Client Basic](https://www.oracle.com/database/technologies/instant-client/downloads.html)
2. Extrair em: `C:\instantclient-basic\instantclient_23_8`
3. Confirmar que `oci.dll` está presente nessa pasta

### 4.3 Dependências Python

```bash
cd app
pip install -r requirements.txt
```

**requirements.txt:**
```
streamlit
openpyxl
oracledb
pydantic
pandas
```

---

## 5. Configuração

Editar o arquivo [app/config.py](app/config.py):

```python
# Caminho do Oracle Instant Client
INSTANTCLIENT_PATH = r"C:\instantclient-basic\instantclient_23_8"

# Conexão Oracle
ORACLE_CONFIG = {
    "user":     "USUARIO",
    "password": "SENHA",
    "dsn": "(DESCRIPTION=(ADDRESS=(PROTOCOL=TCP)(HOST=IP_SERVIDOR)(PORT=1521))(CONNECT_DATA=(SERVICE_NAME=NOME_SERVICE)))",
}

# Valores fixos do negócio
CODCONTA_PADRAO  = 100010   # Conta contábil de comissão
CODFILIAL_PADRAO = "1"      # Filial padrão
TIPOSERVICO      = "99"     # Tipo de serviço (Outros Pag.)
```

**Parâmetros da Rotina 749** (não alterar sem análise do tracer):

| Parâmetro | Valor | Descrição |
|---|---|---|
| CODROTINACAD | 749 | Rotina de origem |
| TIPOLANC | C | Crédito / Confirmado |
| TIPOPARCEIRO | R | RCA / Representante |
| INDICE | A | — |
| MOEDA | R | Real |
| NFSERVICO | N | Não |
| UTILIZOURATEIOCONTA | N | Não |
| PRCRATEIOUTILIZADO | 100 | 100% |
| REINFEVENTOR4040 | N | Não |
| DUPLIC | dinâmico | Igual ao número da parcela |
| CODROTINAALT | A | Confirmado no tracer |

---

## 6. Como Executar

```bash
cd app
python -m streamlit run app.py
```

Acesso: **http://localhost:8501**

Para rodar em segundo plano (Windows):
```powershell
Start-Process python -ArgumentList '-m streamlit run app.py --server.headless false'
```

---

## 7. Fluxo de Uso

```
1. Sidebar → "Testar Conexão"
        │
        ▼
2. Baixar modelo Excel (sidebar)
   Preencher com dados dos RCAs
        │
        ▼
3. Upload da planilha (.xlsx)
   Sistema lê e valida automaticamente:
   - Detecta colunas fixas (parceiro(COD), RCA, contadebito, historico)
   - Detecta colunas de data (cada data = uma parcela)
   - Busca nome do RCA no Oracle (PCUSUARI)
   - Verifica campo BLOQUEIO
        │
        ▼
4. Conferir tabela de preview
   - Linhas amarelas = RCA bloqueado ou não encontrado
   - Badges informativos (lançamentos, RCAs, parcelas, alertas)
        │
        ▼
5. "Executar Gravação na PCLANC"
   - Barra de progresso em tempo real
   - INSERT para cada lançamento
   - Exibe RECNUMs gerados
        │
        ▼
6. Histórico da Sessão
   - Acumula todos os lançamentos gravados
   - Exportar relatório Excel
```

---

## 8. Formato da Planilha Excel

### Colunas fixas obrigatórias

| Coluna | Nome exato | Tipo | Descrição |
|---|---|---|---|
| A | `parceiro(COD)` | Inteiro | Código do RCA na PCUSUARI (CODUSUR) |
| B | `RCA` | Texto | Nome do RCA (referência visual) |
| C | `contadebito` | Inteiro | Código da conta contábil (ex: 100010) |
| D | `historico` | Texto | Descrição do lançamento (ex: COMISSAO ABR/2026) |

### Colunas de parcela (dinâmicas)

Qualquer coluna cujo **cabeçalho seja uma data** no formato `DD/MM/AAAA` é interpretada como uma parcela:

| Coluna | Cabeçalho | Valor | Resultado |
|---|---|---|---|
| E | `13/04/2026` | 7.219,48 | Lançamento parcela 1, DTVENC = 13/04/2026 |
| F | `30/04/2026` | 7.219,48 | Lançamento parcela 2, DTVENC = 30/04/2026 |

- Células vazias nessas colunas são ignoradas
- Valores ≤ 0 são ignorados
- Adicione quantas colunas de data precisar

### Exemplo de planilha

| parceiro(COD) | RCA | contadebito | historico | 13/04/2026 | 30/04/2026 |
|---|---|---|---|---|---|
| 11 | TELMI TEIXEIRA DO LAGO | 100010 | COMISSAO ABR/2026 | 7.219,48 | 7.219,48 |
| 25 | JOSE SANTOS | 100010 | COMISSAO ABR/2026 | 3.450,00 | 3.450,00 |
| 33 | MARIA OLIVEIRA | 100010 | COMISSAO ABR/2026 | 1.890,75 | |

> A linha 3 gera apenas 1 lançamento (parcela 1), pois a coluna 30/04/2026 está vazia.

### Validações no Excel

| Campo | Regra | Indicação visual |
|---|---|---|
| parceiro(COD) | Obrigatório, inteiro 1–999999 | Vermelho se inválido |
| RCA | Obrigatório quando linha preenchida | Vermelho se vazio |
| contadebito | Obrigatório, inteiro > 0 | Vermelho se inválido |
| historico | Obrigatório quando linha preenchida | Vermelho se vazio |
| Valor parcela | Deve ser > 0 | Vermelho se ≤ 0 |

---

## 9. Módulos do Sistema

### 9.1 `config.py`
Centraliza todas as configurações do sistema. Único arquivo a editar para mudança de ambiente (banco, filial, conta).

### 9.2 `models.py`
Modelos Pydantic para tipagem e validação interna:
- `ComissaoRCA` — representa uma linha/parcela lida do Excel
- `ValidacaoItem` — resultado da validação de uma linha
- `ResultadoImportacao` — resultado completo da importação
- `ResultadoGravacao` — resultado da gravação no banco

### 9.3 `excel_parser.py`

**Função principal:** `ler_excel(conteudo_bytes, codfilial_padrao)`

- Lê o arquivo Excel via `openpyxl` (read_only, data_only)
- Mapeia colunas fixas por nome (case-insensitive, aceita variações)
- Detecta colunas de data automaticamente pelo cabeçalho
- Gera um `ComissaoRCA` por combinação linha × coluna-data com valor preenchido
- `parse_valor()` aceita formatos `R$ 7.219,48`, `7219.48`, `7.219,48`

**Aliases aceitos para as colunas fixas:**

| Campo interno | Nomes aceitos no cabeçalho |
|---|---|
| codusur | PARCEIRO(COD), CODUSUR, COD_USUR, COD, CODRCA... |
| nome_rca | RCA, NOME_RCA, NOME RCA, NOME... |
| codconta | CONTADEBITO, CODCONTA, CONTA, CODIGO_CONTA... |
| codfilial | CODFILIAL, FILIAL, COD_FILIAL... |
| historico | HISTORICO, HISTÓRICO, DESCRICAO, OBS... |

### 9.4 `oracle_db.py`

#### `OracleConnection`
Gerencia a conexão com Oracle 11g em modo grosso (thick mode).
- Inicializa o Instant Client na importação do módulo
- Configura NLS: `NLS_DATE_FORMAT='DD/MM/YYYY'`, `NLS_NUMERIC_CHARACTERS='.,'`

#### `ValidadorRCA`
Consultas de validação contra o WinThor:
- `validar_rca(codusur)` — verifica na PCUSUARI
- `validar_conta(codconta)` — verifica na PCCONTA
- `validar_filial(codfilial)` — verifica na PCFILIAL
- `listar_filiais()` / `listar_contas()` — listas para seleção

#### `GravadorPCLANC`
Responsável pelo INSERT na PCLANC.

**`obter_proximo_recnum()`**
```sql
SELECT NVL(PROXNUMLANC,1) FROM PCCONSUM FOR UPDATE
UPDATE PCCONSUM SET PROXNUMLANC = NVL(PROXNUMLANC,1) + 1
COMMIT
```
O `FOR UPDATE` garante que sessões concorrentes não gerem RECNUMs duplicados.

**`inserir_lancamento()`** — campos gravados na PCLANC:

| Campo PCLANC | Origem | Valor |
|---|---|---|
| RECNUM / RECNUMPRINC | PCCONSUM.PROXNUMLANC | Gerado automaticamente |
| DTLANC | Oracle | `TRUNC(SYSDATE)` |
| DTEMISSAO | Oracle | `TRUNC(SYSDATE)` |
| DTCOMPETENCIA | Oracle | `TRUNC(SYSDATE)` |
| CODFILIAL | config.py | `"1"` |
| TIPOLANC | config.py | `"C"` |
| INDICE | config.py | `"A"` |
| MOEDA | config.py | `"R"` |
| CODCONTA | planilha | contadebito |
| HISTORICO | planilha | maiúsculo sem acento |
| HISTORICO2 | sistema | `"(Parcela: N)"` |
| TIPOPARCEIRO | config.py | `"R"` |
| CODFORNEC | planilha | CODUSUR do RCA |
| DTVENC | planilha | data do cabeçalho da coluna |
| VALOR | planilha | valor da célula |
| NFSERVICO | config.py | `"N"` |
| CODROTINACAD | config.py | `749` |
| PARCELA | sistema | número da parcela (`"1"`, `"2"`...) |
| NUMNOTA | fixo | `0` |
| UTILIZOURATEIOCONTA | config.py | `"N"` |
| PRCRATEIOUTILIZADO | config.py | `100` |
| FORNECEDOR | Oracle PCUSUARI | nome do RCA |
| REINFEVENTOR4040 | config.py | `"N"` |
| NOMEFUNC | fixo | `"IMPORTACAO WEB"` |
| VLRUTILIZADOADIANTFORNEC | fixo | `0` |
| DUPLIC | sistema | igual ao número da parcela |
| CODROTINAALT | config.py | `"A"` |
| TIPOSERVICO | config.py | `"99"` |
| AGENDAMENTO | fixo | `NULL` |
| LACREDIGCONECSOCIAL | fixo | `0` |
| OPCAOPAGAMENTOIPVA | fixo | `0` |

### 9.5 `app.py`
Interface Streamlit. Responsabilidades:
- Renderizar sidebar com parâmetros fixos e botão de conexão
- Gerar e disponibilizar o modelo Excel para download
- Receber upload da planilha, chamar `ler_excel()` e buscar nomes no Oracle
- Exibir preview com highlight amarelo em linhas de alerta
- Executar gravação com barra de progresso em tempo real
- Acumular e exibir histórico da sessão com exportação Excel

**Padrão de estado (session_state):**

| Chave | Conteúdo |
|---|---|
| `lancamentos` | Lista de dicts prontos para gravar |
| `log_gravacao` | Resultado da última gravação (RECNUMs) |
| `historico` | Acumulado de todas as gravações da sessão |
| `erro_gravacao` | Mensagem de erro de conexão |

---

## 10. Banco de Dados — Tabelas Envolvidas

| Tabela | Operação | Finalidade |
|---|---|---|
| `PCUSUARI` | SELECT | Buscar nome e verificar BLOQUEIO do RCA |
| `PCCONSUM` | SELECT FOR UPDATE + UPDATE | Obter e incrementar PROXNUMLANC (RECNUM) |
| `PCLANC` | INSERT | Gravar o lançamento de comissão |
| `PCCONTA` | SELECT | Validar conta contábil |
| `PCFILIAL` | SELECT | Validar filial |

### Query PCUSUARI (busca de RCA)
```sql
SELECT NOME, NVL(BLOQUEIO, 'N') AS BLOQUEIO
  FROM PCUSUARI
 WHERE NOME IS NOT NULL
   AND DTTERMINO IS NULL
   AND CODUSUR = :COD
```

### Mecanismo PROXNUMLANC
O WinThor usa `PCCONSUM.PROXNUMLANC` como contador global de RECNUMs para a PCLANC. O sistema replica exatamente o mecanismo original:
1. `SELECT NVL(PROXNUMLANC,1) FROM PCCONSUM FOR UPDATE` — bloqueia a linha
2. Incrementa com `UPDATE PCCONSUM SET PROXNUMLANC = NVL(PROXNUMLANC,1) + 1`
3. `COMMIT` — libera o lock
4. Executa o `INSERT` com o RECNUM obtido

---

## 11. Regras de Negócio

1. **Uma linha Excel = N lançamentos** — um por coluna com data no cabeçalho que tenha valor
2. **DTLANC, DTEMISSAO, DTCOMPETENCIA** = `TRUNC(SYSDATE)` do servidor Oracle (não da máquina do usuário)
3. **DTVENC** = data do cabeçalho da coluna de parcela
4. **HISTORICO** gravado em maiúsculo sem acento (`COMISSAO ABR/2026`)
5. **HISTORICO2** = `(Parcela: N)` onde N é o número da parcela
6. **DUPLIC** = número da parcela (1 para parcela 1, 2 para parcela 2, etc.)
7. **Nome do RCA** vem obrigatoriamente da PCUSUARI — não da planilha
8. **Filial e conta contábil** são fixas (definidas em config.py, não editáveis na interface)
9. Células de parcela vazias ou com valor ≤ 0 são ignoradas silenciosamente

---

## 12. Alertas e Validações

### Na planilha Excel (validação em tempo real no Excel)
- Campos obrigatórios vazios → célula vermelha
- Valor de parcela ≤ 0 → célula vermelha

### No sistema (após upload)
| Situação | Indicação |
|---|---|
| RCA não encontrado na PCUSUARI | Linha amarela + badge vermelho |
| RCA com BLOQUEIO = 'S' | Linha amarela + badge laranja |
| Histórico vazio na planilha | Linha amarela |
| Falha de conexão Oracle | Aviso inline |

---

## 13. Histórico da Sessão

O histórico acumula todos os lançamentos gravados durante a sessão (enquanto o Streamlit não for reiniciado). Para cada gravação são registrados:
- RECNUM gerado
- CODUSUR e nome do RCA
- Parcela, valor, DTVENC
- Histórico
- Status (OK ou mensagem de erro)
- Data/hora da gravação

O histórico pode ser exportado como Excel clicando em **"Baixar Relatório (Excel)"**.

> O histórico é perdido ao reiniciar o servidor Streamlit. Para persistência entre sessões, seria necessário salvar em banco ou arquivo.

---

## 14. Troubleshooting

### Erro: "DPI-1047: Cannot locate a 64-bit Oracle Client library"
O Oracle Instant Client não foi encontrado.
- Verificar se `INSTANTCLIENT_PATH` em `config.py` aponta para a pasta correta
- Confirmar que `oci.dll` existe na pasta
- Confirmar que o Python e o Instant Client são ambos **64-bit**

### Erro de conexão: "ORA-12541: TNS:no listener"
- Verificar se o IP e porta em `ORACLE_CONFIG["dsn"]` estão corretos
- Verificar se o servidor Oracle está acessível pela rede

### Erro: "ORA-12154: TNS:could not resolve the connect identifier"
- Verificar o `SERVICE_NAME` no DSN
- O DSN deve estar no formato completo (não usar tnsnames.ora)

### Planilha não reconhecida
- Verificar se a coluna `parceiro(COD)` existe (nome exato ou variações aceitas)
- Verificar se pelo menos uma coluna de data existe no cabeçalho (formato `DD/MM/AAAA`)

### Nenhum lançamento gerado
- Verificar se as células de valor das colunas de data estão preenchidas
- Verificar se os valores são > 0

### RECNUM duplicado
Não deve ocorrer pois o mecanismo `FOR UPDATE` bloqueia a linha do PROXNUMLANC durante a transação. Se ocorrer, investigar se outra sessão está manipulando PROXNUMLANC fora do padrão WinThor.
