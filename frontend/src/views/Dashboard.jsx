import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboard, getProfiles, createProfile } from '../api/client'

const SCORE_RING = {
  green:  'border-green-400 bg-green-50',
  yellow: 'border-yellow-400 bg-yellow-50',
  gray:   'border-gray-200 bg-white',
}

const SCORE_BADGE_CLS = (score) => {
  if (score >= 0.7) return 'bg-green-100 text-green-800'
  if (score >= 0.4) return 'bg-yellow-100 text-yellow-800'
  return 'bg-gray-100 text-gray-500'
}

// ---------------------------------------------------------------------------
// First-login profile setup prompt
// ---------------------------------------------------------------------------
function ProfileSetup({ onDone }) {
  const [name, setName] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleCreate = async (e) => {
    e.preventDefault()
    if (!name.trim()) { setError('Please enter a profile name.'); return }
    setSaving(true)
    setError('')
    try {
      await createProfile({ name: name.trim() })
      onDone()
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to create profile.')
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm p-8 w-full max-w-md">
        <h1 className="text-xl font-bold text-gray-900 mb-1">Welcome to ProposalPilot</h1>
        <p className="text-sm text-gray-500 mb-6">
          Create a personal profile to get solicitations scored against your research interests.
          You can add capabilities and keywords after setup.
        </p>

        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Your name or profile label
            </label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Larry Bernstein"
              autoFocus
              className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={saving}
            className="w-full py-2 bg-blue-700 text-white text-sm font-medium rounded hover:bg-blue-800 disabled:opacity-50 transition-colors"
          >
            {saving ? 'Creating...' : 'Create Profile'}
          </button>
        </form>

        <div className="mt-6 pt-5 border-t border-gray-100">
          <p className="text-xs text-gray-500 mb-3 font-medium">What happens next:</p>
          <ol className="text-xs text-gray-500 space-y-1.5 list-decimal list-inside">
            <li>Go to <strong>Capabilities</strong> → <strong>Generate from Profile</strong></li>
            <li>Paste your ORCID URL or upload your CV</li>
            <li>Review and save the suggested capability areas</li>
            <li>Click <strong>Score My Profile</strong> to rank solicitations against your expertise</li>
          </ol>
        </div>

        <button
          onClick={() => navigate('/capabilities/generate')}
          className="mt-4 w-full py-2 text-sm text-blue-700 border border-blue-200 rounded hover:bg-blue-50 transition-colors"
        >
          Skip — go to Capability Generation
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Dashboard
// ---------------------------------------------------------------------------
export default function Dashboard() {
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [needsProfile, setNeedsProfile] = useState(false)

  const load = () => {
    setLoading(true)
    Promise.all([getDashboard(), getProfiles()])
      .then(([dash, profiles]) => {
        // Non-shared owned profiles only
        const ownedProfiles = profiles.filter(p => !p.shared)
        if (ownedProfiles.length === 0) {
          setNeedsProfile(true)
        } else {
          setData(dash)
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  if (loading) return <div className="p-8 text-center text-gray-400">Loading...</div>

  if (needsProfile) {
    return <ProfileSetup onDone={() => { setNeedsProfile(false); load() }} />
  }

  const ScoreRow = ({ profileName, scores }) => {
    const visible = (scores || []).filter(s => s.score > 0)
    if (!visible.length) return null
    // Shorten label to first name / first word
    const label = profileName.split(' ')[0]
    return (
      <div className="flex flex-wrap items-start gap-1">
        <span className="text-xs text-gray-400 shrink-0 pt-0.5 w-14 truncate" title={profileName}>
          {label}
        </span>
        <div className="flex flex-wrap gap-1">
          {visible.map((s, i) => (
            <span
              key={i}
              className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs font-medium ${SCORE_BADGE_CLS(s.score)}`}
            >
              <span className="font-mono">{s.score.toFixed(2)}</span>
              <span>{s.capability}</span>
            </span>
          ))}
        </div>
      </div>
    )
  }

  const SolCard = ({ item }) => {
    const ringCls = SCORE_RING[item.score_color] || SCORE_RING.gray
    const hasScores = (item.profile_scores || []).length > 0

    return (
      <div
        className={`rounded-lg border-2 p-4 shadow-sm hover:shadow-md transition-all cursor-pointer ${ringCls}`}
        onClick={() => navigate(`/solicitations/${item.id}`)}
      >
        <div className="flex justify-between items-start mb-2">
          <span className="bg-gray-100 text-gray-700 text-xs font-semibold px-2 py-0.5 rounded">
            {item.agency}
          </span>
          <span className="text-gray-400 font-mono text-xs">{item.topic_number || '-'}</span>
        </div>

        <h3 className="font-semibold text-gray-900 mb-3 line-clamp-2 text-sm leading-snug">
          {item.title}
        </h3>

        {hasScores && (
          <div className="flex flex-col gap-1.5 mb-3">
            {item.profile_scores.map(ps => (
              <ScoreRow
                key={ps.profile_id}
                profileName={ps.profile_name}
                scores={ps.scores}
              />
            ))}
          </div>
        )}

        <div className="flex flex-col gap-0.5 mt-auto">
          {item.open_date && (
            <span className="text-xs text-gray-500">Opens: {item.open_date}</span>
          )}
          {(item.close_date || item.deadline) && (
            <span className="text-xs text-gray-500">Closes: {item.close_date || item.deadline}</span>
          )}
        </div>
      </div>
    )
  }

  const Section = ({ title, items, isSchedule = false, icon, colorClass }) => {
    if (!items || items.length === 0) return null
    return (
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <span className={`text-xl ${colorClass}`}>{icon}</span>
          <h2 className="text-lg font-bold text-gray-800">
            {title}
            <span className="text-sm font-normal text-gray-400 ml-2">({items.length})</span>
          </h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item, idx) => {
            if (isSchedule) {
              return (
                <div key={idx} className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
                  <div className="flex justify-between items-start mb-2">
                    <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2 py-0.5 rounded uppercase">
                      {item.agency}
                    </span>
                    <span className="text-gray-500 text-xs font-medium">{item.solicitation_cycle}</span>
                  </div>
                  <div className="mt-3 text-sm text-gray-700">
                    <p className="mb-1">
                      <span className="font-semibold text-gray-900">Expected Release:</span>{' '}
                      {item.expected_release_month}
                    </p>
                    <p>
                      <span className="font-semibold text-gray-900">Expected Open:</span>{' '}
                      {item.expected_open_month}
                    </p>
                  </div>
                  {item.notes && (
                    <p className="mt-3 text-xs text-gray-500 italic border-t border-gray-100 pt-2">
                      {item.notes}
                    </p>
                  )}
                </div>
              )
            }
            return <SolCard key={item.id} item={item} />
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Agency Release Calendar</h1>
        <p className="text-sm text-gray-500 mt-1">
          Opportunities sorted by alignment strength for your profiles
        </p>
      </div>

      <Section title="Action Required: TPOC Window Active" items={data.tpoc_window}    icon="🚨" colorClass="text-red-600" />
      <Section title="Closing Soon (< 30 days)"            items={data.closing_soon}   icon="⏳" colorClass="text-orange-500" />
      <Section title="Open Now"                            items={data.open_now}       icon="🟢" colorClass="text-green-500" />
      <Section title="Newly Released (last 14 days)"       items={data.newly_released} icon="⭐" colorClass="text-yellow-500" />
      <Section title="Coming Soon (Expected Cycles)"       items={data.coming_soon}    icon="📅" colorClass="text-blue-500" isSchedule={true} />
      <Section title="Recently Closed"                     items={data.recently_closed} icon="🔒" colorClass="text-gray-400" />
    </div>
  )
}
