-- =============================================================================
-- Migration 003 - Permite NULL em importacao_itens.dtlanc
-- (nem todo lancamento tem data de lancamento separada da dt_venc)
-- =============================================================================

USE comissao_rca;

ALTER TABLE importacao_itens
  MODIFY COLUMN dtlanc DATE NULL;

-- Confirma
DESCRIBE importacao_itens;
