import { Link, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
import { getProfiles, createProfile } from '../api/client'

export default function NavBar() {
  const { pathname } = useLocation()
  const [profiles, setProfiles] = useState([])
  const [selectedProfileId, setSelectedProfileId] = useState(() => {
    return localStorage.getItem('profileId') || '1'
  })

  useEffect(() => {
    getProfiles().then(setProfiles).catch(console.error)
  }, [])

  const handleProfileChange = (e) => {
    const val = e.target.value
    if (val === 'NEW') {
      const name = prompt('Enter new profile name:')
      if (name) {
        createProfile({ name }).then((res) => {
          localStorage.setItem('profileId', res.id)
          window.location.reload()
        })
      }
    } else {
      localStorage.setItem('profileId', val)
      window.location.reload()
    }
  }

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
      </div>
      
      <div className="flex items-center gap-4 text-sm">
        <button
          onClick={() => { localStorage.removeItem('token'); window.location.href = '/login' }}
          className="text-blue-300 hover:text-white text-xs transition-colors"
        >
          Sign out
        </button>
        <span className="text-blue-200">Profile:</span>
        <select 
          value={selectedProfileId}
          onChange={handleProfileChange}
          className="bg-blue-800 text-white border border-blue-700 rounded px-2 py-1 outline-none focus:ring-1 focus:ring-blue-500"
        >
          {profiles.map(p => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
          <option disabled>---</option>
          <option value="NEW">+ Create New...</option>
        </select>
      </div>
    </nav>
  )
}
