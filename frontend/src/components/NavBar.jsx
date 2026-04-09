import { Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { getProfiles } from '../api/client'

export default function NavBar() {
  const { pathname } = useLocation()
  const isAdmin = sessionStorage.getItem('is_admin') === 'true'

  const [profiles, setProfiles] = useState([])
  const [selectedProfileId, setSelectedProfileId] = useState(
    () => localStorage.getItem('adminProfileId') || ''
  )

  useEffect(() => {
    if (!isAdmin) return
    getProfiles().then(ps => {
      setProfiles(ps)
      if (!selectedProfileId && ps.length > 0) {
        setSelectedProfileId(String(ps[0].id))
        localStorage.setItem('adminProfileId', String(ps[0].id))
      }
    }).catch(console.error)
  }, [isAdmin])

  const handleProfileChange = (e) => {
    const val = e.target.value
    setSelectedProfileId(val)
    localStorage.setItem('adminProfileId', val)
    // Reload so dashboard and solicitation list pick up the new context
    window.location.reload()
  }

  const isLoggedIn = !!sessionStorage.getItem('token')

  const link = (to, label) => (
    <Link
      to={to}
      className={`px-3 py-2 rounded text-sm font-medium transition-colors ${
        pathname === to
          ? 'bg-blue-700 text-white'
          : 'text-blue-100 hover:bg-blue-700 hover:text-white'
      }`}
    >
      {label}
    </Link>
  )

  return (
    <nav className="bg-blue-900 text-white px-6 py-3 flex items-center justify-between shadow">
      <div className="flex items-center gap-6">
        <Link to="/" className="text-white font-bold text-lg tracking-tight mr-4">
          ProposalPilot
        </Link>
        {link('/', 'Dashboard')}
        {link('/solicitations', 'Solicitations')}
        {link('/keywords', 'Keywords')}
        {link('/capabilities', 'Capabilities')}
        {isAdmin && link('/admin', 'Admin')}
      </div>

      <div className="flex items-center gap-4 text-sm">
        {isLoggedIn && (
          <Link
            to="/change-password"
            className="text-blue-300 hover:text-white text-xs transition-colors"
          >
            Change Password
          </Link>
        )}
        {isAdmin && profiles.length > 0 && (
          <>
            <span className="text-blue-400 text-xs">Viewing as:</span>
            <select
              value={selectedProfileId}
              onChange={handleProfileChange}
              className="bg-blue-800 text-white border border-blue-700 rounded px-2 py-1 text-xs outline-none focus:ring-1 focus:ring-blue-500"
            >
              {profiles.map(p => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </>
        )}
        <button
          onClick={() => {
            sessionStorage.removeItem('token')
            sessionStorage.removeItem('is_admin')
            window.location.href = '/login'
          }}
          className="text-blue-300 hover:text-white text-xs transition-colors"
        >
          Sign out
        </button>
      </div>
    </nav>
  )
}
