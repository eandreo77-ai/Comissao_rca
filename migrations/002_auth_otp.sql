-- =============================================================================
-- Migration 002 - Login OTP por email (passwordless magic-link-ish)
-- =============================================================================

USE comissao_rca;

-- 1. Adiciona coluna email em usuarios
--    NOT NULL UNIQUE. Como ja temos 1 registro (admin) sem email, vou
--    primeiro adicionar como NULLable, popular o admin, depois forcar NOT NULL.
ALTER TABLE usuarios
  ADD COLUMN IF NOT EXISTS email VARCHAR(120) UNIQUE AFTER username;

-- 2. Senha_hash agora opcional (login eh por OTP, nao por senha)
ALTER TABLE usuarios
  MODIFY COLUMN senha_hash VARCHAR(255) NULL;

-- 3. Atualiza admin existente com email do owner inicial
UPDATE usuarios
   SET email = 'eduardo.oliveira@rofedistribuidora.com.br'
 WHERE username = 'admin' AND (email IS NULL OR email = '');

-- 4. Tabela de tokens (codigos OTP)
CREATE TABLE IF NOT EXISTS auth_tokens (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id   INT NOT NULL,
  codigo       VARCHAR(20) NOT NULL,
  dt_gerado    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  dt_expira    DATETIME NOT NULL,
  usado        TINYINT(1) NOT NULL DEFAULT 0,
  ip_origem    VARCHAR(45) NULL,
  user_agent   VARCHAR(255) NULL,
  CONSTRAINT fk_token_user FOREIGN KEY (usuario_id)
    REFERENCES usuarios(id) ON DELETE CASCADE,
  INDEX idx_codigo (codigo, usado),
  INDEX idx_expira (dt_expira)
) ENGINE=InnoDB;

-- 5. Tabela de sessoes ativas (opcional, pra logout server-side futuro)
CREATE TABLE IF NOT EXISTS sessoes (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id    INT NOT NULL,
  session_id    VARCHAR(64) UNIQUE NOT NULL,
  dt_inicio     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  dt_ultimo_uso DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                ON UPDATE CURRENT_TIMESTAMP,
  ip_origem     VARCHAR(45),
  user_agent    VARCHAR(255),
  ativa         TINYINT(1) NOT NULL DEFAULT 1,
  CONSTRAINT fk_sess_user FOREIGN KEY (usuario_id)
    REFERENCES usuarios(id) ON DELETE CASCADE,
  INDEX idx_ativa (session_id, ativa)
) ENGINE=InnoDB;

-- 6. Confirma o que ficou
SELECT id, username, email, perfil, ativo FROM usuarios;
