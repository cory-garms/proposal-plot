import { Link, useLocation } from 'react-router-dom'

export default function NavBar() {
  const { pathname } = useLocation()

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
    <nav className="bg-blue-900 text-white px-6 py-3 flex items-center gap-6 shadow">
      <Link to="/" className="text-white font-bold text-lg tracking-tight mr-4">
        ProposalPilot
      </Link>
      {link('/', 'Solicitations')}
    </nav>
  )
}
