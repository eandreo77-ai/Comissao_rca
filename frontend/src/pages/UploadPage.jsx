import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadExcel } from '../services/api'

function UploadPage() {
  const [arquivo, setArquivo] = useState(null)
  const [dtReferencia, setDtReferencia] = useState('')
  const [loading, setLoading] = useState(false)
  const [mensagem, setMensagem] = useState(null)
  const [dragover, setDragover] = useState(false)
  const fileInputRef = useRef(null)
  const navigate = useNavigate()

  // Gera opções de mês/ano para os últimos 3 meses
  const gerarOpcoesMes = () => {
    const opcoes = []
    const hoje = new Date()
    for (let i = 0; i < 3; i++) {
      const d = new Date(hoje.getFullYear(), hoje.getMonth() - i, 1)
      const mes = String(d.getMonth() + 1).padStart(2, '0')
      const ano = d.getFullYear()
      opcoes.push({ value: `${mes}/${ano}`, label: `${mes}/${ano}` })
    }
    return opcoes
  }

  const handleFileSelect = (e) => {
    const file = e.target.files[0]
    if (file) {
      if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        setMensagem({ tipo: 'error', texto: 'Selecione um arquivo Excel (.xlsx ou .xls)' })
        return
      }
      setArquivo(file)
      setMensagem(null)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    setDragover(false)
    const file = e.dataTransfer.files[0]
    if (file) {
      if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
        setMensagem({ tipo: 'error', texto: 'Selecione um arquivo Excel (.xlsx ou .xls)' })
        return
      }
      setArquivo(file)
      setMensagem(null)
    }
  }

  const handleSubmit = async () => {
    if (!arquivo) {
      setMensagem({ tipo: 'error', texto: 'Selecione um arquivo Excel' })
      return
    }
    if (!dtReferencia) {
      setMensagem({ tipo: 'error', texto: 'Selecione o mês de referência' })
      return
    }

    setLoading(true)
    setMensagem(null)

    try {
      const response = await uploadExcel(arquivo, dtReferencia)
      const data = response.data
      setMensagem({
        tipo: 'success',
        texto: `Planilha importada com sucesso! ${data.resultado.total_linhas} linhas processadas.`,
      })

      // Redireciona para detalhe após 1.5s
      setTimeout(() => {
        navigate(`/importacoes/${data.importacao_id}`)
      }, 1500)
    } catch (error) {
      const erroMsg = error.response?.data?.erro || error.message || 'Erro ao importar planilha'
      setMensagem({ tipo: 'error', texto: erroMsg })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div className="card">
        <h2 className="card-title">Importar Planilha de Comissão</h2>

        {mensagem && (
          <div className={`alert alert-${mensagem.tipo}`}>
            {mensagem.texto}
          </div>
        )}

        <div className="form-row" style={{ marginBottom: '20px' }}>
          <div className="form-group">
            <label>Mês de Referência</label>
            <select
              value={dtReferencia}
              onChange={(e) => setDtReferencia(e.target.value)}
            >
              <option value="">Selecione...</option>
              {gerarOpcoesMes().map((op) => (
                <option key={op.value} value={op.value}>{op.label}</option>
              ))}
            </select>
          </div>
        </div>

        <div
          className={`upload-area ${dragover ? 'dragover' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragover(true) }}
          onDragLeave={() => setDragover(false)}
          onDrop={handleDrop}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xls"
            onChange={handleFileSelect}
          />
          <div className="upload-icon">📊</div>
          {arquivo ? (
            <div>
              <strong>{arquivo.name}</strong>
              <p style={{ color: 'var(--text-light)', marginTop: '4px' }}>
                {(arquivo.size / 1024).toFixed(1)} KB
              </p>
            </div>
          ) : (
            <div>
              <p><strong>Clique aqui ou arraste o arquivo Excel</strong></p>
              <p style={{ color: 'var(--text-light)', marginTop: '4px' }}>
                Formatos aceitos: .xlsx, .xls
              </p>
            </div>
          )}
        </div>

        <div className="actions-bar">
          <button
            className="btn btn-primary"
            onClick={handleSubmit}
            disabled={loading || !arquivo || !dtReferencia}
          >
            {loading ? <><span className="spinner"></span> Importando...</> : 'Importar Planilha'}
          </button>

          {arquivo && (
            <button
              className="btn btn-outline"
              onClick={() => { setArquivo(null); setMensagem(null) }}
            >
              Limpar
            </button>
          )}
        </div>
      </div>

      {/* Legenda da planilha */}
      <div className="card">
        <h2 className="card-title">Formato da Planilha Esperado</h2>
        <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Coluna</th>
                <th>Campo</th>
                <th>Tipo</th>
                <th>Obrigatório</th>
                <th>Exemplo</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>A</td><td>CODUSUR</td><td>Número</td><td>Sim</td><td>11</td></tr>
              <tr><td>B</td><td>NOME_RCA</td><td>Texto</td><td>Não</td><td>TELMI TEIXEIRA</td></tr>
              <tr><td>C</td><td>CODFILIAL</td><td>Texto</td><td>Sim</td><td>1</td></tr>
              <tr><td>D</td><td>VALOR</td><td>Decimal</td><td>Sim</td><td>7219.48</td></tr>
              <tr><td>E</td><td>CODCONTA</td><td>Número</td><td>Sim</td><td>100010</td></tr>
              <tr><td>F</td><td>DTLANC</td><td>Data</td><td>Sim</td><td>07/04/2026</td></tr>
              <tr><td>G</td><td>DTVENC</td><td>Data</td><td>Sim</td><td>08/04/2026</td></tr>
              <tr><td>H</td><td>HISTORICO</td><td>Texto</td><td>Não</td><td>Comissão Mar/2026</td></tr>
            </tbody>
          </table>
        </div>
        <p style={{ marginTop: '12px', color: 'var(--text-light)', fontSize: '0.85rem' }}>
          A primeira linha deve conter os cabeçalhos. Os dados iniciam na linha 2.
        </p>
      </div>
    </div>
  )
}

export default UploadPage
