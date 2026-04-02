import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import NavBar from './components/NavBar'
import SolicitationList from './views/SolicitationList'
import SolicitationDetail from './views/SolicitationDetail'
import DraftEditor from './views/DraftEditor'
import Dashboard from './views/Dashboard'
import Keywords from './views/Keywords'
import Login from './views/Login'

function AppShell() {
  const { pathname } = useLocation()
  const hideNav = pathname === '/login'

  return (
    <div className="min-h-screen bg-gray-50">
      {!hideNav && <NavBar />}
      <main>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Dashboard />} />
          <Route path="/solicitations" element={<SolicitationList />} />
          <Route path="/solicitations/:id" element={<SolicitationDetail />} />
          <Route path="/projects/:id" element={<DraftEditor />} />
          <Route path="/keywords" element={<Keywords />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  )
}
