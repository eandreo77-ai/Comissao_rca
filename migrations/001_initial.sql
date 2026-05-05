-- =============================================================================
-- Schema MariaDB do sistema Comissao RCA
-- Versao: 001 (inicial)
-- Engine: InnoDB (default)
-- Charset: utf8mb4 (default em MariaDB 10.11+)
--
-- Compativel com a API atual do app/pix_db.py (rca_pix, rca_ignorar):
--   - mesmos nomes de tabela e colunas
--   - tipo_chave virou ENUM (espelha TIPOS_VALIDOS no Python)
--   - dt_atualizacao / dt_inclusao viraram DATETIME (eram TEXT em SQLite)
--
-- Tabelas novas:
--   - usuarios            (login do app)
--   - configuracoes       (CODCONTA padrao, CODFILIAL etc - antes hardcoded)
--   - importacoes         (cabecalho de cada importacao)
--   - importacao_itens    (cada lancamento gerado, RECNUM espelhado da Oracle)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS comissao_rca
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE comissao_rca;

-- =============================================================================
-- 1. USUARIOS DO APP
-- =============================================================================
CREATE TABLE IF NOT EXISTS usuarios (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(50)  NOT NULL UNIQUE,
  nome          VARCHAR(120) NOT NULL,
  senha_hash    VARCHAR(255) NOT NULL,
  perfil        ENUM('admin','operador') NOT NULL DEFAULT 'operador',
  ativo         TINYINT(1)   NOT NULL DEFAULT 1,
  ultimo_login  DATETIME     NULL,
  criado_em     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ativo (ativo)
) ENGINE=InnoDB;

-- =============================================================================
-- 2. CHAVES PIX DOS RCAs (espelho da rca_pix do SQLite)
-- =============================================================================
CREATE TABLE IF NOT EXISTS rca_pix (
  codrca          INT          NOT NULL PRIMARY KEY,
  nome_rca        VARCHAR(120) NOT NULL,
  chave_pix       VARCHAR(120) NOT NULL,
  tipo_chave      ENUM('CPF','CNPJ','EMAIL','TELEFONE','ALEATORIA') NOT NULL,
  dt_atualizacao  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                               ON UPDATE CURRENT_TIMESTAMP,
  usuario         VARCHAR(50)  NULL,
  INDEX idx_nome (nome_rca)
) ENGINE=InnoDB;

-- =============================================================================
-- 3. RCAs IGNORADOS (espelho da rca_ignorar do SQLite)
-- =============================================================================
CREATE TABLE IF NOT EXISTS rca_ignorar (
  codrca       INT          NOT NULL PRIMARY KEY,
  motivo       VARCHAR(255) NOT NULL DEFAULT '',
  dt_inclusao  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- =============================================================================
-- 4. CONFIGURACOES DINAMICAS (antes hardcoded em config.py)
-- =============================================================================
CREATE TABLE IF NOT EXISTS configuracoes (
  chave          VARCHAR(50)  NOT NULL PRIMARY KEY,
  valor          VARCHAR(255) NOT NULL,
  descricao      TEXT         NULL,
  atualizado_em  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
  atualizado_por INT          NULL,
  CONSTRAINT fk_config_user FOREIGN KEY (atualizado_por)
    REFERENCES usuarios(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- Seed das configs hoje hardcoded em config.py.
-- INSERT IGNORE preserva valores se o admin mudou via UI (re-rodar o schema nao reverte).
INSERT IGNORE INTO configuracoes (chave, valor, descricao) VALUES
  ('CODCONTA_PADRAO',  '100010', 'Conta contabil padrao de comissao (PCCONTA)'),
  ('CODFILIAL_PADRAO', '1',      'Filial padrao dos lancamentos (PCFILIAL)'),
  ('TIPOSERVICO',      '99',     'Tipo de servico (99 = Outros Pagamentos)'),
  ('CODROTINACAD',     '749',    'Codigo da rotina geradora no WinThor');

-- =============================================================================
-- 5. IMPORTACOES (cabecalho) - auditoria de cada planilha processada
-- =============================================================================
CREATE TABLE IF NOT EXISTS importacoes (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id     INT          NOT NULL,
  arquivo_nome   VARCHAR(255) NULL,
  total_itens    INT          NOT NULL DEFAULT 0,
  valor_total    DECIMAL(15,2) NOT NULL DEFAULT 0,
  status         ENUM('rascunho','validado','gravado','erro','cancelado')
                 NOT NULL DEFAULT 'rascunho',
  iniciada_em    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  finalizada_em  DATETIME     NULL,
  erro_msg       TEXT         NULL,
  observacao     TEXT         NULL,
  CONSTRAINT fk_imp_user FOREIGN KEY (usuario_id)
    REFERENCES usuarios(id) ON DELETE RESTRICT,
  INDEX idx_status (status),
  INDEX idx_data   (iniciada_em),
  INDEX idx_user   (usuario_id)
) ENGINE=InnoDB;

-- =============================================================================
-- 6. ITENS DA IMPORTACAO - 1 linha = 1 INSERT que foi (ou sera) feito na PCLANC
-- =============================================================================
CREATE TABLE IF NOT EXISTS importacao_itens (
  id             INT AUTO_INCREMENT PRIMARY KEY,
  importacao_id  INT          NOT NULL,
  linha_excel    INT          NULL,
  parcela        TINYINT      NOT NULL DEFAULT 1,
  codusur        INT          NOT NULL,
  nome_rca       VARCHAR(120) NULL,
  codfilial      VARCHAR(4)   NULL,
  codconta       INT          NULL,
  valor          DECIMAL(15,2) NOT NULL,
  dtlanc         DATE         NOT NULL,
  dtvenc         DATE         NOT NULL,
  historico      VARCHAR(255) NULL,
  recnum_oracle  BIGINT       NULL,
  status         ENUM('pendente','validado','erro','gravado') NOT NULL DEFAULT 'pendente',
  erro_msg       TEXT         NULL,
  CONSTRAINT fk_item_imp FOREIGN KEY (importacao_id)
    REFERENCES importacoes(id) ON DELETE CASCADE,
  INDEX idx_recnum (recnum_oracle),
  INDEX idx_codusur (codusur)
) ENGINE=InnoDB;

-- =============================================================================
-- 7. USUARIO ADMIN INICIAL
-- Hash bcrypt rounds=12. Senha NAO armazenada em claro.
-- Para regerar: rode no console Python "bcrypt.hashpw(...)" com bcrypt.gensalt(rounds=12).
-- =============================================================================
INSERT IGNORE INTO usuarios (username, nome, senha_hash, perfil) VALUES
  ('admin', 'Administrador', '$2b$12$22FIzkEL.qwsE.EQrVyBVufqX48BvOpYdMiCPhNfjznI9ACWPHjlq', 'admin');
