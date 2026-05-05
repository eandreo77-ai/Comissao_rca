import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { listarImportacoes } from '../services/api'

const statusBadge = {
  P: 'badge-pendente',
  V: 'badge-validado',
  E: 'badge-erro',
  G: 'badge-gravado',
  C: 'badge-cancelado',
}

function ImportacoesPage() {
  const [importacoes, setImportacoes] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    carregarDados()
  }, [])

  const carregarDados = async () => {
    try {
      const response = await listarImportacoes()
      setImportacoes(response.data)
    } catch (error) {
      console.error('Erro ao carregar importações:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatarValor = (valor) => {
    return new Intl.NumberFormat('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    }).format(valor)
  }

  if (loading) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '40px' }}>
        <div className="spinner" style={{ borderTopColor: 'var(--primary)', borderColor: 'var(--border)' }}></div>
        <p style={{ marginTop: '12px', color: 'var(--text-light)' }}>Carregando...</p>
      </div>
    )
  }

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h2 className="card-title" style={{ marginBottom: 0, borderBottom: 'none', paddingBottom: 0 }}>
            Importações Realizadas
          </h2>
          <Link to="/" className="btn btn-primary btn-sm">Nova Importação</Link>
        </div>

        {importacoes.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--text-light)' }}>
            <p>Nenhuma importação realizada ainda.</p>
            <Link to="/" className="btn btn-primary" style={{ marginTop: '12px' }}>
              Importar Planilha
            </Link>
          </div>
        ) : (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Arquivo</th>
                  <th>Referência</th>
                  <th>Data Import.</th>
                  <th>Linhas</th>
                  <th>Valor Total</th>
                  <th>Erros</th>
                  <th>Status</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {importacoes.map((imp) => (
                  <tr key={imp.id}>
                    <td>{imp.id}</td>
                    <td>{imp.arquivo_nome}</td>
                    <td>{imp.dt_referencia}</td>
                    <td>{imp.dt_importacao}</td>
                    <td>{imp.total_linhas}</td>
                    <td>{formatarValor(imp.total_valor)}</td>
                    <td style={{ color: imp.total_erros > 0 ? 'var(--danger)' : 'inherit' }}>
                      {imp.total_erros}
                    </td>
                    <td>
                      <span className={`badge ${statusBadge[imp.status] || ''}`}>
                        {imp.status_display}
                      </span>
                    </td>
                    <td>
                      <Link to={`/importacoes/${imp.id}`} className="btn btn-outline btn-sm">
                        Ver Detalhes
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default ImportacoesPage
