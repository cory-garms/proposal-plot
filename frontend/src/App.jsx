import { BrowserRouter, Routes, Route, useLocation, Navigate } from 'react-router-dom'
import { useState, useEffect } from 'react'
import NavBar from './components/NavBar'
import SolicitationList from './views/SolicitationList'
import SolicitationDetail from './views/SolicitationDetail'
import DraftEditor from './views/DraftEditor'
import Dashboard from './views/Dashboard'
import Keywords from './views/Keywords'
import Admin from './views/Admin'
import Capabilities from './views/Capabilities'
import Login from './views/Login'
import ChangePassword from './views/ChangePassword'
import GenerateCapabilities from './views/GenerateCapabilities'
import { getMe } from './api/client'

function RequireAuth({ children }) {
  const [status, setStatus] = useState('checking')  // 'checking' | 'ok' | 'unauth'

  useEffect(() => {
    const token = sessionStorage.getItem('token')
    if (!token) { setStatus('unauth'); return }
    getMe()
      .then(user => {
        // Refresh is_admin in case it changed server-side
        sessionStorage.setItem('is_admin', user.is_admin ? 'true' : 'false')
        setStatus('ok')
      })
      .catch(() => {
        sessionStorage.removeItem('token')
        sessionStorage.removeItem('is_admin')
        setStatus('unauth')
      })
  }, [])

  if (status === 'checking') return null
  if (status === 'unauth') return <Navigate to="/login" replace />
  return children
}

function AppShell() {
  const { pathname } = useLocation()
  const hideNav = pathname === '/login'

  return (
    <div className="min-h-screen bg-gray-50">
      {!hideNav && <NavBar />}
      <main>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<RequireAuth><Dashboard /></RequireAuth>} />
          <Route path="/solicitations" element={<RequireAuth><SolicitationList /></RequireAuth>} />
          <Route path="/solicitations/:id" element={<RequireAuth><SolicitationDetail /></RequireAuth>} />
          <Route path="/projects/:id" element={<RequireAuth><DraftEditor /></RequireAuth>} />
          <Route path="/keywords" element={<RequireAuth><Keywords /></RequireAuth>} />
          <Route path="/admin" element={<RequireAuth><Admin /></RequireAuth>} />
          <Route path="/capabilities" element={<RequireAuth><Capabilities /></RequireAuth>} />
          <Route path="/change-password" element={<RequireAuth><ChangePassword /></RequireAuth>} />
          <Route path="/capabilities/generate" element={<RequireAuth><GenerateCapabilities /></RequireAuth>} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter basename={import.meta.env.BASE_URL}>
      <AppShell />
    </BrowserRouter>
  )
}
