import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import { getCapabilities, createCapability, updateCapability, deleteCapability, getProfiles, runAlignment, getAlignStatus } from '../api/client'

const EMPTY_FORM = { name: '', description: '', keywords: '', profile_id: 1 }

function KeywordChips({ keywords }) {
  const visible = keywords.slice(0, 8)
  const extra = keywords.length - visible.length
  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {visible.map((kw, i) => (
        <span key={i} className="bg-blue-50 text-blue-700 text-xs px-2 py-0.5 rounded font-mono">
          {kw}
        </span>
      ))}
      {extra > 0 && (
        <span className="text-xs text-gray-400 px-1 py-0.5">+{extra} more</span>
      )}
    </div>
  )
}

function CapabilityForm({ profiles, initial, onSave, onCancel }) {
  const [form, setForm] = useState(
    initial
      ? { ...initial, keywords: (initial.keywords || []).join(', ') }
      : EMPTY_FORM
  )
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim() || !form.description.trim()) {
      setError('Name and description are required.')
      return
    }
    setSaving(true)
    setError('')
    const keywords = form.keywords
      .split(',')
      .map(k => k.trim().toLowerCase())
      .filter(Boolean)
    try {
      if (initial) {
        await updateCapability(initial.id, { name: form.name, description: form.description, keywords })
      } else {
        await createCapability({ name: form.name, description: form.description, keywords, profile_id: Number(form.profile_id) })
      }
      onSave()
    } catch (err) {
      setError(err.response?.data?.detail || 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-blue-50 border border-blue-200 rounded-lg p-5 mb-4">
      <div className="grid grid-cols-1 gap-3 mb-3">
        <div className="flex gap-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-600 mb-1">Name</label>
            <input
              type="text"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g. Hyperspectral Imaging"
            />
          </div>
          {!initial && (
            <div className="w-40">
              <label className="block text-xs font-medium text-gray-600 mb-1">Profile</label>
              <select
                value={form.profile_id}
                onChange={e => setForm(f => ({ ...f, profile_id: e.target.value }))}
                className="w-full text-sm border border-gray-200 rounded px-2 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </div>
          )}
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
          <textarea
            value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            rows={3}
            className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
            placeholder="Describe this technical capability..."
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Keywords (comma-separated)</label>
          <input
            type="text"
            value={form.keywords}
            onChange={e => setForm(f => ({ ...f, keywords: e.target.value }))}
            className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="lidar, point cloud, 3d reconstruction, ..."
          />
        </div>
      </div>

      {error && <p className="text-xs text-red-500 mb-2">{error}</p>}

      <div className="flex gap-2">
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-1.5 bg-blue-700 text-white text-sm font-medium rounded hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {saving ? 'Saving...' : (initial ? 'Save Changes' : 'Add Capability')}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-1.5 text-sm text-gray-600 border border-gray-200 rounded hover:bg-gray-100 transition-colors"
        >
          Cancel
        </button>
      </div>
    </form>
  )
}

function CapabilityCard({ cap, onEdit, onDelete, editable }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 shadow-sm">
      <div className="flex items-start justify-between gap-2 mb-1">
        <h3 className="font-semibold text-gray-900 text-sm">{cap.name}</h3>
        <div className="flex gap-2 shrink-0">
          {editable ? (
            <>
              <button
                onClick={() => onEdit(cap)}
                className="text-xs text-blue-600 hover:text-blue-800 transition-colors"
              >
                Edit
              </button>
              <button
                onClick={() => onDelete(cap)}
                className="text-xs text-red-400 hover:text-red-600 transition-colors"
              >
                Delete
              </button>
            </>
          ) : (
            <span className="text-xs text-gray-300 italic">read-only</span>
          )}
        </div>
      </div>
      <p className="text-xs text-gray-500 leading-relaxed">{cap.description}</p>
      {cap.keywords?.length > 0 && <KeywordChips keywords={cap.keywords} />}
    </div>
  )
}

export default function Capabilities() {
  const [caps, setCaps] = useState([])
  const [profiles, setProfiles] = useState([])
  const [loading, setLoading] = useState(true)
  const [profileFilter, setProfileFilter] = useState('all')
  const [showAdd, setShowAdd] = useState(false)
  const [editing, setEditing] = useState(null)
  const [scoring, setScoring] = useState(false)
  const [scoreMsg, setScoreMsg] = useState('')
  const pollRef = useRef(null)
  const isAdmin = sessionStorage.getItem('is_admin') === 'true'

  const load = () => {
    const profileId = profileFilter !== 'all' ? profileFilter : undefined
    return getCapabilities(profileId)
      .then(setCaps)
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    getProfiles().then(setProfiles).catch(console.error)
  }, [])

  useEffect(() => {
    setLoading(true)
    load()
  }, [profileFilter])

  const handleSave = () => {
    setShowAdd(false)
    setEditing(null)
    load()
  }

  const handleScore = async () => {
    const selectedProfile = profiles.find(p => String(p.id) === String(profileFilter))
    if (profileFilter === 'all' || !selectedProfile) {
      setScoreMsg('Select a specific profile to score.')
      return
    }
    if (selectedProfile.shared) {
      setScoreMsg('You can only score your own profiles, not shared ones.')
      return
    }
    setScoring(true)
    setScoreMsg('')
    try {
      await runAlignment({ profile_id: Number(profileFilter), skip_scored: true, include_expired: false })
      // Poll until done
      pollRef.current = setInterval(async () => {
        try {
          const s = await getAlignStatus()
          if (!s.running) {
            clearInterval(pollRef.current)
            pollRef.current = null
            setScoring(false)
            const st = s.last_stats
            setScoreMsg(st
              ? `Done — ${st.solicitations_scored} solicitations scored, ${st.api_calls_made} LLM calls.`
              : 'Scoring complete.')
          }
        } catch { /* ignore poll errors */ }
      }, 3000)
    } catch (e) {
      setScoring(false)
      setScoreMsg(e.response?.data?.detail || 'Scoring failed.')
    }
  }

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const handleDelete = async (cap) => {
    if (!confirm(`Delete capability "${cap.name}"? This cannot be undone.`)) return
    setCaps(prev => prev.filter(c => c.id !== cap.id))
    try {
      await deleteCapability(cap.id)
    } catch {
      load()
    }
  }

  const ownedProfileIds = new Set(
    profiles.filter(p => !p.shared).map(p => p.id)
  )

  const grouped = profiles.length > 0
    ? profiles.map(p => ({
        profile: p,
        items: caps.filter(c => c.profile_id === p.id),
        editable: isAdmin || ownedProfileIds.has(p.id),
      })).filter(g => g.items.length > 0)
    : [{ profile: null, items: caps, editable: isAdmin }]

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Capabilities</h1>
          <p className="text-xs text-gray-500 mt-0.5">{caps.length} capabilities across {profiles.length} profiles</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={profileFilter}
            onChange={e => { setProfileFilter(e.target.value); setScoreMsg('') }}
            className="text-sm border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All profiles</option>
            {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          {!isAdmin && !showAdd && !editing && (() => {
            const sel = profiles.find(p => String(p.id) === String(profileFilter))
            const canScore = profileFilter !== 'all' && sel && !sel.shared
            return (
              <button
                onClick={handleScore}
                disabled={scoring || !canScore}
                title={!canScore ? 'Select your own profile to score' : 'Score solicitations against this profile'}
                className="px-4 py-1.5 bg-green-700 text-white text-sm font-medium rounded hover:bg-green-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {scoring ? 'Scoring...' : 'Score My Profile'}
              </button>
            )
          })()}
          {!showAdd && !editing && (
            <>
              <Link
                to="/capabilities/generate"
                className="px-4 py-1.5 bg-purple-700 text-white text-sm font-medium rounded hover:bg-purple-800 transition-colors"
              >
                Generate from Profile
              </Link>
              <button
                onClick={() => setShowAdd(true)}
                className="px-4 py-1.5 bg-blue-700 text-white text-sm font-medium rounded hover:bg-blue-800 transition-colors"
              >
                + Add Capability
              </button>
            </>
          )}
        </div>
      </div>
      {scoreMsg && (
        <p className={`text-xs mb-4 ${scoreMsg.includes('failed') || scoreMsg.includes('Select') ? 'text-red-500' : 'text-green-700'}`}>
          {scoreMsg}
        </p>
      )}

      {showAdd && (
        <CapabilityForm
          profiles={isAdmin ? profiles : profiles.filter(p => !p.shared)}
          initial={null}
          onSave={handleSave}
          onCancel={() => setShowAdd(false)}
        />
      )}

      {loading ? (
        <div className="text-center text-gray-400 py-12">Loading...</div>
      ) : caps.length === 0 ? (
        <div className="text-center text-gray-400 py-12">No capabilities found.</div>
      ) : (
        grouped.map(({ profile, items, editable }) => (
          <div key={profile?.id ?? 'all'} className="mb-8">
            {profile && (
              <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
                {profile.name}
                {!!profile.shared && (
                  <span className="ml-2 text-xs font-normal text-gray-400 normal-case tracking-normal">
                    (shared — read-only)
                  </span>
                )}
              </h2>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {items.map(cap => (
                editing?.id === cap.id ? (
                  <div key={cap.id} className="md:col-span-2">
                    <CapabilityForm
                      profiles={profiles.filter(p => !p.shared)}
                      initial={editing}
                      onSave={handleSave}
                      onCancel={() => setEditing(null)}
                    />
                  </div>
                ) : (
                  <CapabilityCard
                    key={cap.id}
                    cap={cap}
                    onEdit={setEditing}
                    onDelete={handleDelete}
                    editable={editable}
                  />
                )
              ))}
            </div>
          </div>
        ))
      )}
    </div>
  )
}
