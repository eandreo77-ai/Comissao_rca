/**
 * Serviço de API para comunicação com o backend Django.
 */
import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Accept': 'application/json',
  },
})

// ---- Upload ----
export const uploadExcel = (arquivo, dtReferencia) => {
  const formData = new FormData()
  formData.append('arquivo', arquivo)
  formData.append('dt_referencia', dtReferencia)
  return api.post('/upload/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ---- Importações ----
export const listarImportacoes = () => api.get('/importacoes/')

export const detalheImportacao = (id) => api.get(`/importacoes/${id}/`)

export const cancelarImportacao = (id) => api.delete(`/importacoes/${id}/`)

// ---- Validação e Gravação ----
export const validarImportacao = (id) => api.post(`/validar/${id}/`)

export const gravarImportacao = (id) => api.post(`/gravar/${id}/`)

export default api
