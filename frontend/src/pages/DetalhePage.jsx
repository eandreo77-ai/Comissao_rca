import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import {
  detalheImportacao,
  validarImportacao,
  gravarImportacao,
  cancelarImportacao,
} from '../services/api'

const statusBadge = {
  P: 'badge-pendente',
  V: 'badge-validado',
  E: 'badge-erro',
  G: 'badge-gravado',
  C: 'badge-cancelado',
}

const statusLabel = {
  P: 'Pendente',
  V: 'Validado',
  E: 'Com Erro',
  G: 'Gravado',
  C: 'Cancelado',
}

function DetalhePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [importacao, setImportacao] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(null)
  const [mensagem, setMensagem] = useState(null)

  useEffect(() => {
    carregarDados()
  }, [id])

  const carregarDados = async () => {
    try {
      const response = await detalheImportacao(id)
      setImportacao(response.data)
    } catch (error) {
      console.error('Erro ao carregar detalhe:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleValidar = async () => {
    setActionLoading('validar')
    setMensagem(null)
    try {
      const response = await validarImportacao(id)
      const data = response.data
      setMensagem({
        tipo: 'success',
        texto: `Validação concluída: ${data.validados} validados, ${data.erros} com erro.`,
      })
      await carregarDados()
    } catch (error) {
      setMensagem({ tipo: 'error', texto: error.response?.data?.erro || 'Erro ao validar' })
    } finally {
      setActionLoading(null)
    }
  }

  const handleGravar = async () => {
    if (!window.confirm('Confirma a gravação dos itens validados no Contas a Pagar?')) return

    setActionLoading('gravar')
    setMensagem(null)
    try {
      const response = await gravarImportacao(id)
      const data = response.data
      setMensagem({
        tipo: 'success',
        texto: `Gravação concluída: ${data.gravados} gravados, ${data.erros} com erro.`,
      })
      await carregarDados()
    } catch (error) {
      setMensagem({ tipo: 'error', texto: error.response?.data?.erro || 'Erro ao gravar' })
    } finally {
      setActionLoading(null)
    }
  }

  const handleCancelar = async () => {
    if (!window.confirm('Tem certeza que deseja cancelar esta importação?')) return

    setActionLoading('cancelar')
    try {
      await cancelarImportacao(id)
      setMensagem({ tipo: 'warning', texto: 'Importação cancelada.' })
      await carregarDados()
    } catch (error) {
      setMensagem({ tipo: 'error', texto: error.response?.data?.erro || 'Erro ao cancelar' })
    } finally {
      setActionLoading(null)
    }
  }

  const formatarValor = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(valor)
  }

  const formatarData = (data) => {
    if (!data) return '-'
    // Se já vem formatado DD/MM/YYYY, retorna direto
    if (typeof data === 'string' && data.includes('/')) return data
    return new Date(data).toLocaleDateString('pt-BR')
  }

  if (loading) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
        <div className="spinner" style={{ borderTopColor: 'var(--primary)', borderColor: 'var(--border)' }}></div>
        <p style={{ marginTop: '12px', color: 'var(--text-light)' }}>Carregando...</p>
      </div>
    )
  }

  if (!importacao) {
    return (
      <div className="card">
        <p>Importação não encontrada.</p>
        <Link to="/importacoes" className="btn btn-outline" style={{ marginTop: '12px' }}>
          Voltar
        </Link>
      </div>
    )
  }

  const itensPendentes = importacao.itens?.filter(i => i.status === 'P').length || 0
  const itensValidados = importacao.itens?.filter(i => i.status === 'V').length || 0
  const itensErro = importacao.itens?.filter(i => i.status === 'E').length || 0
  const itensGravados = importacao.itens?.filter(i => i.status === 'G').length || 0

  return (
    <div>
      {/* Header com botão voltar */}
      <div style={{ marginBottom: '16px' }}>
        <Link to="/importacoes" style={{ color: 'var(--primary)', textDecoration: 'none', fontSize: '0.9rem' }}>
          ← Voltar para Importações
        </Link>
      </div>

      {mensagem && (
        <div className={`alert alert-${mensagem.tipo}`}>
          {mensagem.texto}
        </div>
      )}

      {/* Resumo */}
      <div className="card">
        <h2 className="card-title">
          {importacao.arquivo_nome}
          <span className={`badge ${statusBadge[importacao.status]}`} style={{ marginLeft: '12px' }}>
            {importacao.status_display}
          </span>
        </h2>

        <div className="stats-row">
          <div className="stat-card">
            <div className="stat-value">{importacao.total_linhas}</div>
            <div className="stat-label">Total Linhas</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: 'var(--success)' }}>
              {formatarValor(importacao.total_valor)}
            </div>
            <div className="stat-label">Valor Total</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: itensValidados > 0 ? 'var(--success)' : 'inherit' }}>
              {itensValidados}
            </div>
            <div className="stat-label">Validados</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: itensErro > 0 ? 'var(--danger)' : 'inherit' }}>
              {itensErro}
            </div>
            <div className="stat-label">Com Erro</div>
          </div>
          <div className="stat-card">
            <div className="stat-value" style={{ color: 'var(--primary)' }}>
              {itensGravados}
            </div>
            <div className="stat-label">Gravados</div>
          </div>
        </div>

        <div style={{ fontSize: '0.85rem', color: 'var(--text-light)' }}>
          <strong>Referência:</strong> {importacao.dt_referencia} &nbsp;|&nbsp;
          <strong>Importado em:</strong> {importacao.dt_importacao} &nbsp;|&nbsp;
          <strong>Usuário:</strong> {importacao.usuario}
        </div>

        {/* Botões de ação */}
        {importacao.status !== 'G' && importacao.status !== 'C' && (
          <div className="actions-bar">
            {itensPendentes > 0 && (
              <button
                className="btn btn-primary"
                onClick={handleValidar}
                disabled={actionLoading !== null}
              >
                {actionLoading === 'validar'
                  ? <><span className="spinner"></span> Validando...</>
                  : `Validar ${itensPendentes} Itens`}
              </button>
            )}

            {itensValidados > 0 && (
              <button
                className="btn btn-success"
                onClick={handleGravar}
                disabled={actionLoading !== null}
              >
                {actionLoading === 'gravar'
                  ? <><span className="spinner"></span> Gravando...</>
                  : `Gravar ${itensValidados} Itens no Contas a Pagar`}
              </button>
            )}

            <button
              className="btn btn-danger btn-sm"
              onClick={handleCancelar}
              disabled={actionLoading !== null}
            >
              Cancelar Importação
            </button>
          </div>
        )}
      </div>

      {/* Tabela de itens */}
      <div className="card">
        <h2 className="card-title">Itens da Planilha ({importacao.itens?.length || 0})</h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Linha</th>
                <th>CODUSUR</th>
                <th>Nome RCA</th>
                <th>Filial</th>
                <th>Valor</th>
                <th>Conta</th>
                <th>Dt. Lanç.</th>
                <th>Dt. Venc.</th>
                <th>Histórico</th>
                <th>Status</th>
                <th>RECNUM</th>
                <th>Erro</th>
              </tr>
            </thead>
            <tbody>
              {importacao.itens?.map((item) => (
                <tr key={item.id} style={{
                  background: item.status === 'E' ? '#fef2f2' : item.status === 'G' ? '#f0fdf4' : 'inherit'
                }}>
                  <td>{item.linha_excel}</td>
                  <td>{item.codusur}</td>
                  <td>{item.nome_rca_banco || item.nome_rca || '-'}</td>
                  <td>{item.codfilial}</td>
                  <td style={{ textAlign: 'right' }}>{formatarValor(item.valor)}</td>
                  <td>{item.codconta}</td>
                  <td>{formatarData(item.dtlanc)}</td>
                  <td>{formatarData(item.dtvenc)}</td>
                  <td style={{ maxWidth: '150px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.historico || '-'}
                  </td>
                  <td>
                    <span className={`badge ${statusBadge[item.status]}`}>
                      {statusLabel[item.status]}
                    </span>
                  </td>
                  <td>{item.recnum || '-'}</td>
                  <td style={{ color: 'var(--danger)', maxWidth: '200px', fontSize: '0.8rem' }}>
                    {item.erro_msg || '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default DetalhePage
