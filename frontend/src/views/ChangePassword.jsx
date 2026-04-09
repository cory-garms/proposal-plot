import { useState } from 'react'
import { changePassword } from '../api/client'

export default function ChangePassword() {
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess(false)

    if (next.length < 8) {
      setError('New password must be at least 8 characters.')
      return
    }
    if (next !== confirm) {
      setError('New passwords do not match.')
      return
    }
    if (current === next) {
      setError('New password must differ from current password.')
      return
    }

    setLoading(true)
    try {
      await changePassword(current, next)
      setSuccess(true)
      setCurrent('')
      setNext('')
      setConfirm('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Password change failed.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="p-6 max-w-md mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Change Password</h1>
      <p className="text-sm text-gray-500 mb-6">
        Choose a strong password you haven't used elsewhere.
      </p>

      {success && (
        <div className="mb-4 px-4 py-3 bg-green-50 border border-green-200 rounded text-sm text-green-800">
          Password updated successfully.
        </div>
      )}

      {error && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded text-sm text-red-700">
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Current password
          </label>
          <input
            type="password"
            value={current}
            onChange={e => setCurrent(e.target.value)}
            required
            autoComplete="current-password"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            New password
          </label>
          <input
            type="password"
            value={next}
            onChange={e => setNext(e.target.value)}
            required
            autoComplete="new-password"
            minLength={8}
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-400 mt-1">Minimum 8 characters.</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Confirm new password
          </label>
          <input
            type="password"
            value={confirm}
            onChange={e => setConfirm(e.target.value)}
            required
            autoComplete="new-password"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2 bg-blue-700 text-white text-sm font-medium rounded hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? 'Updating...' : 'Update Password'}
        </button>
      </form>

      <div className="mt-8 p-4 bg-blue-50 border border-blue-100 rounded text-sm text-blue-800">
        <p className="font-semibold mb-2">Getting started with ProposalPilot</p>
        <ol className="list-decimal list-inside space-y-1 text-blue-700">
          <li>Change your temporary password above (you're here).</li>
          <li>
            Go to <strong>Capabilities</strong> to create a personal profile based on
            your research interests. Add capability areas and keywords — these drive
            how solicitations are scored for you.
          </li>
          <li>
            Browse <strong>Solicitations</strong> to see opportunities ranked by
            alignment with your capabilities.
          </li>
          <li>
            Open a solicitation and click <strong>Create Project</strong> to generate
            a draft Technical Volume or Commercialization Plan.
          </li>
        </ol>
        <p className="mt-2 text-xs text-blue-600">
          The <strong>Spectral Sciences</strong> profile is pre-loaded with company-wide
          capabilities — use it as a starting point or reference.
        </p>
      </div>
    </div>
  )
}
