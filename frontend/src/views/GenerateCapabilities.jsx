import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  generateCapabilitiesFromUrl,
  generateCapabilitiesFromFile,
  createCapability,
  getProfiles,
} from '../api/client'

// ---------------------------------------------------------------------------
// Step 1 — input source
// ---------------------------------------------------------------------------
function SourceStep({ onGenerated }) {
  const [mode, setMode] = useState('url')   // 'url' | 'file'
  const [url, setUrl] = useState('')
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      let result
      if (mode === 'url') {
        if (!url.trim()) { setError('Please enter a URL or ORCID ID.'); setLoading(false); return }
        result = await generateCapabilitiesFromUrl(url.trim())
      } else {
        if (!file) { setError('Please select a PDF or DOCX file.'); setLoading(false); return }
        result = await generateCapabilitiesFromFile(file)
      }
      onGenerated(result.capabilities)
    } catch (err) {
      setError(err.response?.data?.detail || 'Generation failed. Check your input and try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="flex gap-3 mb-2">
        {['url', 'file'].map(m => (
          <button
            key={m}
            type="button"
            onClick={() => { setMode(m); setError('') }}
            className={`px-4 py-1.5 rounded text-sm font-medium border transition-colors ${
              mode === m
                ? 'bg-blue-700 text-white border-blue-700'
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {m === 'url' ? 'URL / ORCID' : 'Upload CV'}
          </button>
        ))}
      </div>

      {mode === 'url' ? (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            ORCID profile URL or any researcher profile URL
          </label>
          <input
            type="text"
            value={url}
            onChange={e => setUrl(e.target.value)}
            placeholder="https://orcid.org/0000-0002-1605-0331"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-400 mt-1">
            Works best with ORCID profiles, faculty pages, and lab pages. Paywalled journal pages will not work.
          </p>
        </div>
      ) : (
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Upload your CV or publication list (PDF or DOCX, max 10 MB)
          </label>
          <input
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={e => setFile(e.target.files[0] || null)}
            className="block w-full text-sm text-gray-500 file:mr-3 file:py-1.5 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={loading}
        className="px-6 py-2 bg-blue-700 text-white text-sm font-medium rounded hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? 'Analyzing profile...' : 'Generate Capabilities'}
      </button>

      {loading && (
        <p className="text-xs text-gray-400">
          This takes 15–30 seconds. The AI is reading your profile and identifying technical capability areas.
        </p>
      )}
    </form>
  )
}


// ---------------------------------------------------------------------------
// Step 2 — review and edit each generated capability
// ---------------------------------------------------------------------------
function ReviewStep({ capabilities: initial, onSave, onBack }) {
  const [caps, setCaps] = useState(
    initial.map((c, i) => ({
      ...c,
      keywordsStr: (c.keywords || []).join(', '),
      include: true,
      id: i,
    }))
  )
  const [profiles, setProfiles] = useState([])
  const [profileId, setProfileId] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useState(() => {
    getProfiles().then(ps => {
      setProfiles(ps)
      if (ps.length > 0) setProfileId(String(ps[0].id))
    }).catch(() => {})
  })

  const update = (id, field, value) =>
    setCaps(prev => prev.map(c => c.id === id ? { ...c, [field]: value } : c))

  const handleSave = async () => {
    const toSave = caps.filter(c => c.include)
    if (toSave.length === 0) { setError('Select at least one capability to save.'); return }
    if (!profileId) { setError('Select a profile.'); return }
    setSaving(true)
    setError('')
    try {
      for (const cap of toSave) {
        const keywords = cap.keywordsStr
          .split(',')
          .map(k => k.trim().toLowerCase())
          .filter(Boolean)
        await createCapability({
          name: cap.name,
          description: cap.description,
          keywords,
          profile_id: Number(profileId),
        })
      }
      onSave(toSave.length)
    } catch (err) {
      setError(err.response?.data?.detail || 'Save failed.')
      setSaving(false)
    }
  }

  return (
    <div>
      <div className="flex items-center gap-4 mb-5">
        <div>
          <label className="text-sm font-medium text-gray-700 mr-2">Save to profile:</label>
          <select
            value={profileId}
            onChange={e => setProfileId(e.target.value)}
            className="text-sm border border-gray-300 rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <span className="text-xs text-gray-400">
          {caps.filter(c => c.include).length} of {caps.length} selected
        </span>
      </div>

      <div className="space-y-4 mb-6">
        {caps.map(cap => (
          <div
            key={cap.id}
            className={`border rounded-lg p-4 transition-colors ${
              cap.include ? 'border-blue-200 bg-blue-50' : 'border-gray-200 bg-gray-50 opacity-60'
            }`}
          >
            <div className="flex items-start gap-3">
              <input
                type="checkbox"
                checked={cap.include}
                onChange={e => update(cap.id, 'include', e.target.checked)}
                className="mt-1 rounded"
              />
              <div className="flex-1 space-y-2">
                <input
                  type="text"
                  value={cap.name}
                  onChange={e => update(cap.id, 'name', e.target.value)}
                  disabled={!cap.include}
                  className="w-full font-semibold text-sm border-0 bg-transparent focus:outline-none focus:ring-1 focus:ring-blue-400 rounded px-1 disabled:text-gray-400"
                />
                <textarea
                  value={cap.description}
                  onChange={e => update(cap.id, 'description', e.target.value)}
                  disabled={!cap.include}
                  rows={3}
                  className="w-full text-xs text-gray-600 border border-gray-200 rounded px-2 py-1.5 resize-none focus:outline-none focus:ring-1 focus:ring-blue-400 disabled:opacity-50 bg-white"
                />
                <div>
                  <label className="text-xs text-gray-500">Keywords (comma-separated)</label>
                  <input
                    type="text"
                    value={cap.keywordsStr}
                    onChange={e => update(cap.id, 'keywordsStr', e.target.value)}
                    disabled={!cap.include}
                    className="w-full text-xs border border-gray-200 rounded px-2 py-1 mt-0.5 focus:outline-none focus:ring-1 focus:ring-blue-400 disabled:opacity-50 bg-white"
                  />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {error && <p className="text-sm text-red-600 mb-3">{error}</p>}

      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2 bg-blue-700 text-white text-sm font-medium rounded hover:bg-blue-800 disabled:opacity-50 transition-colors"
        >
          {saving ? 'Saving...' : `Save ${caps.filter(c => c.include).length} Capabilities`}
        </button>
        <button
          onClick={onBack}
          disabled={saving}
          className="px-4 py-2 text-sm text-gray-600 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
        >
          Back
        </button>
      </div>
    </div>
  )
}


// ---------------------------------------------------------------------------
// Main view
// ---------------------------------------------------------------------------
export default function GenerateCapabilities() {
  const navigate = useNavigate()
  const [step, setStep] = useState('source')   // 'source' | 'review' | 'done'
  const [capabilities, setCapabilities] = useState([])
  const [savedCount, setSavedCount] = useState(0)

  const handleGenerated = (caps) => {
    setCapabilities(caps)
    setStep('review')
  }

  const handleSaved = (count) => {
    setSavedCount(count)
    setStep('done')
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-xl font-bold text-gray-900">Generate Capabilities from Profile</h1>
        <p className="text-sm text-gray-500 mt-1">
          Provide an ORCID URL, any researcher profile URL, or upload your CV.
          The AI will suggest capability areas and keywords — you review and edit before anything is saved.
        </p>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8 text-xs text-gray-400">
        {['source', 'review', 'done'].map((s, i) => (
          <div key={s} className="flex items-center gap-2">
            <span className={`w-5 h-5 rounded-full flex items-center justify-center font-medium ${
              step === s ? 'bg-blue-700 text-white' :
              ['source','review','done'].indexOf(step) > i ? 'bg-green-600 text-white' :
              'bg-gray-200 text-gray-500'
            }`}>{i + 1}</span>
            <span className={step === s ? 'text-gray-700 font-medium' : ''}>
              {s === 'source' ? 'Input' : s === 'review' ? 'Review & Edit' : 'Done'}
            </span>
            {i < 2 && <span className="text-gray-200">—</span>}
          </div>
        ))}
      </div>

      {step === 'source' && (
        <SourceStep onGenerated={handleGenerated} />
      )}

      {step === 'review' && (
        <ReviewStep
          capabilities={capabilities}
          onSave={handleSaved}
          onBack={() => setStep('source')}
        />
      )}

      {step === 'done' && (
        <div className="text-center py-12">
          <div className="text-4xl mb-4">✓</div>
          <h2 className="text-lg font-semibold text-gray-900 mb-2">
            {savedCount} {savedCount === 1 ? 'capability' : 'capabilities'} saved
          </h2>
          <p className="text-sm text-gray-500 mb-6">
            Go to Capabilities to review them, or score your profile against open solicitations.
          </p>
          <div className="flex justify-center gap-3">
            <button
              onClick={() => navigate('/capabilities')}
              className="px-5 py-2 bg-blue-700 text-white text-sm font-medium rounded hover:bg-blue-800 transition-colors"
            >
              View Capabilities
            </button>
            <button
              onClick={() => { setStep('source'); setCapabilities([]) }}
              className="px-5 py-2 text-sm text-gray-600 border border-gray-300 rounded hover:bg-gray-50 transition-colors"
            >
              Generate More
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
