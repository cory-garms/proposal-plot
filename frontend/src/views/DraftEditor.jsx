import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getProject, getDrafts, generateDraft, updateDraft } from '../api/client'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const SECTION_TYPES = [
  { value: 'technical_volume', label: 'Technical Volume' },
  { value: 'commercialization_plan', label: 'Commercialization Plan' },
]

const TONES = [
  { value: 'technical', label: 'Technical' },
  { value: 'executive', label: 'Executive' },
  { value: 'persuasive', label: 'Persuasive' },
]

const FOCUS_AREAS = [
  { value: 'balanced', label: 'Balanced' },
  { value: 'innovation', label: 'Innovation' },
  { value: 'feasibility', label: 'Feasibility' },
  { value: 'commercialization', label: 'Commercialization' },
]

const scoreColor = (score) => {
  if (score >= 0.7) return 'text-green-600'
  if (score >= 0.4) return 'text-yellow-600'
  return 'text-gray-400'
}

export default function DraftEditor() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)
  const [drafts, setDrafts] = useState([])
  const [selectedDraftId, setSelectedDraftId] = useState(null)
  const [sectionType, setSectionType] = useState('technical_volume')
  const [tone, setTone] = useState('technical')
  const [focusArea, setFocusArea] = useState('balanced')
  const [generating, setGenerating] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  const [editing, setEditing] = useState(false)
  const [editContent, setEditContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    Promise.all([getProject(id), getDrafts(id)])
      .then(([p, d]) => {
        setProject(p)
        setDrafts(d)
        if (d.length > 0) setSelectedDraftId(d[0].id)
      })
      .catch(() => setError('Failed to load project'))
      .finally(() => setLoading(false))
  }, [id])

  const handleGenerate = async () => {
    setGenerating(true)
    setError('')
    try {
      const draft = await generateDraft(id, sectionType, tone, focusArea)
      setDrafts(prev => [draft, ...prev])
      setSelectedDraftId(draft.id)
    } catch (e) {
      const msg = e.response?.data?.detail || e.message || 'Generation failed'
      setError(msg)
    } finally {
      setGenerating(false)
    }
  }

  const handleCopy = () => {
    const draft = drafts.find(d => d.id === selectedDraftId)
    if (!draft) return
    navigator.clipboard.writeText(editing ? editContent : draft.content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  const handleEdit = () => {
    const draft = drafts.find(d => d.id === selectedDraftId)
    if (!draft) return
    setEditContent(draft.content)
    setEditing(true)
    setSaved(false)
  }

  const handleCancelEdit = () => {
    setEditing(false)
    setEditContent('')
  }

  const handleSave = async () => {
    if (!editContent.trim()) return
    setSaving(true)
    setError('')
    try {
      const updated = await updateDraft(id, selectedDraftId, editContent)
      setDrafts(prev => prev.map(d => d.id === updated.id ? updated : d))
      setEditing(false)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (e) {
      setError('Save failed: ' + (e.response?.data?.detail || e.message || 'unknown'))
    } finally {
      setSaving(false)
    }
  }

  const selectedDraft = drafts.find(d => d.id === selectedDraftId)

  if (loading) return <div className="p-8 text-center text-gray-400">Loading project...</div>
  if (error && !project) return <div className="p-8 text-center text-red-500">{error}</div>
  if (!project) return null

  const solTitle = project.title
  const topScore = project.alignment_scores?.[0]

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <button
        onClick={() => navigate(`/solicitations/${project.solicitation_id}`)}
        className="text-sm text-blue-600 hover:underline mb-4 inline-block"
      >
        &larr; Back to solicitation
      </button>

      {/* Project header */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-5 mb-5">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900">{solTitle}</h1>
            <p className="text-xs text-gray-500 mt-1">Project #{project.id} &middot; {project.status}</p>
          </div>
          {topScore && (
            <div className="text-right shrink-0">
              <span className={`text-lg font-mono font-bold ${scoreColor(topScore.score)}`}>
                {topScore.score.toFixed(2)}
              </span>
              <p className="text-xs text-gray-500">{topScore.capability}</p>
            </div>
          )}
        </div>

        {/* Alignment summary strip */}
        {project.alignment_scores?.length > 0 && (
          <div className="flex gap-4 mt-3 pt-3 border-t border-gray-100">
            {project.alignment_scores.map(s => (
              <div key={s.capability_id} className="flex items-center gap-1.5">
                <div className={`w-2 h-2 rounded-full ${
                  s.score >= 0.7 ? 'bg-green-500' : s.score >= 0.4 ? 'bg-yellow-400' : 'bg-gray-200'
                }`} />
                <span className="text-xs text-gray-600">{s.capability}</span>
                <span className={`text-xs font-mono font-medium ${scoreColor(s.score)}`}>
                  {s.score.toFixed(2)}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
        {/* Left sidebar: generate controls + draft list */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
            <h2 className="text-sm font-semibold text-gray-700 mb-3">Generate Draft</h2>
            <label className="block text-xs text-gray-500 mb-1">Section type</label>
            <select
              value={sectionType}
              onChange={e => setSectionType(e.target.value)}
              className="w-full text-sm border border-gray-200 rounded px-2 py-1.5 mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {SECTION_TYPES.map(t => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <label className="block text-xs text-gray-500 mb-1">Tone</label>
            <select
              value={tone}
              onChange={e => setTone(e.target.value)}
              className="w-full text-sm border border-gray-200 rounded px-2 py-1.5 mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {TONES.map(t => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
            <label className="block text-xs text-gray-500 mb-1">Focus area</label>
            <select
              value={focusArea}
              onChange={e => setFocusArea(e.target.value)}
              className="w-full text-sm border border-gray-200 rounded px-2 py-1.5 mb-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {FOCUS_AREAS.map(f => (
                <option key={f.value} value={f.value}>{f.label}</option>
              ))}
            </select>
            <button
              onClick={handleGenerate}
              disabled={generating}
              className="w-full px-3 py-2 bg-blue-700 text-white text-sm font-medium rounded hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {generating ? 'Generating...' : 'Generate'}
            </button>
            {generating && (
              <p className="text-xs text-gray-400 mt-2 text-center">
                Calling Claude API...
              </p>
            )}
            {error && (
              <p className="text-xs text-red-500 mt-2">{error}</p>
            )}
          </div>

          {drafts.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-4">
              <h2 className="text-sm font-semibold text-gray-700 mb-2">Draft History</h2>
              <div className="space-y-1">
                {drafts.map(d => (
                  <button
                    key={d.id}
                    onClick={() => { setSelectedDraftId(d.id); setEditing(false); setSaved(false) }}
                    className={`w-full text-left px-2 py-1.5 rounded text-xs transition-colors ${
                      d.id === selectedDraftId
                        ? 'bg-blue-50 text-blue-700 font-medium'
                        : 'text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    <div className="font-medium">{SECTION_TYPES.find(t => t.value === d.section_type)?.label || d.section_type}</div>
                    <div className="text-gray-400">{d.generated_at?.slice(0, 16)}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right: draft content */}
        <div className="lg:col-span-3">
          {selectedDraft ? (
            <div className="bg-white border border-gray-200 rounded-lg shadow-sm">
              <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
                <div>
                  <span className="text-sm font-semibold text-gray-800">
                    {SECTION_TYPES.find(t => t.value === selectedDraft.section_type)?.label}
                  </span>
                  <span className="text-xs text-gray-400 ml-2">{selectedDraft.model_version}</span>
                  {saved && <span className="text-xs text-green-600 ml-2">Saved</span>}
                </div>
                <div className="flex items-center gap-2">
                  {editing ? (
                    <>
                      <button
                        onClick={handleCancelEdit}
                        disabled={saving}
                        className="text-xs px-3 py-1 border border-gray-200 rounded hover:bg-gray-50 disabled:opacity-50 transition-colors"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleSave}
                        disabled={saving}
                        className="text-xs px-3 py-1 bg-blue-700 text-white rounded hover:bg-blue-800 disabled:opacity-50 transition-colors"
                      >
                        {saving ? 'Saving...' : 'Save'}
                      </button>
                    </>
                  ) : (
                    <>
                      <a
                        href={`${API_BASE}/projects/${id}/drafts/${selectedDraft.id}/export/pdf`}
                        download
                        className="text-xs px-3 py-1 border border-gray-200 rounded hover:bg-gray-50 transition-colors"
                      >
                        PDF
                      </a>
                      <a
                        href={`${API_BASE}/projects/${id}/drafts/${selectedDraft.id}/export/docx`}
                        download
                        className="text-xs px-3 py-1 border border-gray-200 rounded hover:bg-gray-50 transition-colors"
                      >
                        DOCX
                      </a>
                      <button
                        onClick={handleEdit}
                        className="text-xs px-3 py-1 border border-gray-200 rounded hover:bg-gray-50 transition-colors"
                      >
                        Edit
                      </button>
                      <button
                        onClick={handleCopy}
                        className="text-xs px-3 py-1 border border-gray-200 rounded hover:bg-gray-50 transition-colors"
                      >
                        {copied ? 'Copied!' : 'Copy'}
                      </button>
                    </>
                  )}
                </div>
              </div>
              {editing ? (
                <textarea
                  value={editContent}
                  onChange={e => setEditContent(e.target.value)}
                  className="w-full p-5 text-sm text-gray-800 leading-relaxed font-mono focus:outline-none resize-none"
                  style={{ minHeight: '70vh' }}
                />
              ) : (
                <div className="p-5 text-sm text-gray-800 whitespace-pre-wrap leading-relaxed font-mono max-h-[70vh] overflow-y-auto">
                  {selectedDraft.content}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-white border border-gray-200 rounded-lg shadow-sm flex items-center justify-center h-64">
              <div className="text-center text-gray-400">
                <p className="text-sm">No draft yet.</p>
                <p className="text-xs mt-1">Select a section type and click Generate.</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
