import { Routes, Route, Link, useLocation } from 'react-router-dom'
import UploadPage from './pages/UploadPage'
import ImportacoesPage from './pages/ImportacoesPage'
import DetalhePage from './pages/DetalhePage'

function App() {
  const location = useLocation()

  return (
    <div className="app-container">
      <header className="header">
        <div>
          <h1>Comissão RCA</h1>
          <span className="header-subtitle">Rofe Distribuidora</span>
        </div>
        <nav className="nav-links">
          <Link to="/" className={location.pathname === '/' ? 'active' : ''}>
            Upload
          </Link>
          <Link to="/importacoes" className={location.pathname.startsWith('/importacoes') ? 'active' : ''}>
            Importações
          </Link>
        </nav>
      </header>

      <main className="main-content">
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/importacoes" element={<ImportacoesPage />} />
          <Route path="/importacoes/:id" element={<DetalhePage />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
