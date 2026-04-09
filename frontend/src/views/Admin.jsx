import { useState, useEffect, useRef } from 'react'
import {
  triggerScrape, getScrapeStatus,
  triggerGrantsScrape, getGrantsScrapeStatus,
  triggerSamScrape, getSamScrapeStatus,
  triggerSamCsvImport, getSamCsvImportStatus,
  runAlignment, getAlignStatus, getProfiles,
} from '../api/client'
import api from '../api/client'

const SCRAPERS = [
  {
    id: 'sbir',
    label: 'SBIR / DOD',
    description: 'Scrapes SBIR.gov and DOD portals using Playwright. Slower — fetches detail pages.',
    defaultMax: 50,
    maxLabel: 'Max pages',
    trigger: (max) => triggerScrape({ max_pages: max }),
    getStatus: getScrapeStatus,
    statsLabel: (s) => s.last_count != null ? `${s.last_count} solicitations last run` : null,
  },
  {
    id: 'grants',
    label: 'Grants.gov',
    description: 'Searches Grants.gov API across 20+ domain clusters. No API key required.',
    defaultMax: 200,
    maxLabel: 'Max results',
    trigger: (max) => triggerGrantsScrape({ max_results: max }),
    getStatus: getGrantsScrapeStatus,
    statsLabel: (s) => s.last_stats
      ? `${s.last_stats.persisted} persisted, ${s.last_stats.errors} errors`
      : null,
  },
  {
    id: 'sam',
    label: 'SAM.gov',
    description: 'Queries SAM.gov across 20 domain clusters. Set SAM_API_KEY in .env for full speed (~10x faster).',
    defaultMax: 100,
    maxLabel: 'Max results',
    trigger: (max) => triggerSamScrape({ max_results: max }),
    getStatus: getSamScrapeStatus,
    statsLabel: (s) => s.last_stats
      ? `${s.last_stats.persisted} persisted, ${s.last_stats.errors} errors`
      : null,
  },
]


function ScraperCard({ config }) {
  const [maxVal, setMaxVal] = useState(config.defaultMax)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const pollRef = useRef(null)

  const fetchStatus = async () => {
    try {
      const s = await config.getStatus()
      setStatus(s)
      if (!s.running && pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    } catch {}
  }

  useEffect(() => {
    fetchStatus()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const handleRun = async () => {
    setError('')
    try {
      await config.trigger(maxVal)
      pollRef.current = setInterval(fetchStatus, 3000)
      fetchStatus()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to start scrape')
    }
  }

  const running = status?.running
  const statsLabel = status ? config.statsLabel(status) : null

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
      <div className="flex items-start justify-between mb-1">
        <h3 className="font-semibold text-gray-900">{config.label}</h3>
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
          running ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-500'
        }`}>
          {running ? 'Running...' : 'Idle'}
        </span>
      </div>

      <p className="text-xs text-gray-500 mb-4">{config.description}</p>

      <div className="flex items-center gap-2 mb-3">
        <label className="text-xs text-gray-500 whitespace-nowrap">{config.maxLabel}</label>
        <input
          type="number"
          value={maxVal}
          onChange={e => setMaxVal(Number(e.target.value))}
          min={1}
          disabled={running}
          className="w-24 text-sm border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        />
        <button
          onClick={handleRun}
          disabled={running}
          className="px-4 py-1.5 bg-blue-700 text-white text-sm font-medium rounded hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Run
        </button>
      </div>

      {error && <p className="text-xs text-red-500 mb-1">{error}</p>}
      {statsLabel && <p className="text-xs text-gray-400">{statsLabel}</p>}
      {status?.last_error && (
        <p className="text-xs text-red-400 mt-1">Last error: {status.last_error}</p>
      )}
    </div>
  )
}


function SamCsvCard() {
  const [filename, setFilename] = useState('SAM_ContractOpportunitiesFull.csv')
  const [maxResults, setMaxResults] = useState(500)
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const pollRef = useRef(null)

  const fetchStatus = async () => {
    try {
      const s = await getSamCsvImportStatus()
      setStatus(s)
      if (!s.running && pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    } catch {}
  }

  useEffect(() => {
    fetchStatus()
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const handleRun = async () => {
    setError('')
    try {
      await triggerSamCsvImport({ filename, max_results: maxResults })
      pollRef.current = setInterval(fetchStatus, 2000)
      fetchStatus()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to start import')
    }
  }

  const running = status?.running
  const stats = status?.last_stats

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
      <div className="flex items-start justify-between mb-1">
        <h3 className="font-semibold text-gray-900">SAM.gov CSV Import</h3>
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
          running ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-500'
        }`}>
          {running ? 'Running...' : 'Idle'}
        </span>
      </div>
      <p className="text-xs text-gray-500 mb-4">
        Import from a bulk extract downloaded at{' '}
        <span className="font-mono">sam.gov/data-services</span>.
        Place the file in the project root directory.
      </p>

      <div className="flex flex-col gap-2 mb-3">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500 w-20 shrink-0">Filename</label>
          <input
            type="text"
            value={filename}
            onChange={e => setFilename(e.target.value)}
            disabled={running}
            className="flex-1 text-sm border border-gray-200 rounded px-2 py-1 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500 w-20 shrink-0">Max results</label>
          <input
            type="number"
            value={maxResults}
            onChange={e => setMaxResults(Number(e.target.value))}
            min={1}
            disabled={running}
            className="w-24 text-sm border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          />
          <button
            onClick={handleRun}
            disabled={running}
            className="px-4 py-1.5 bg-blue-700 text-white text-sm font-medium rounded hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Import
          </button>
        </div>
      </div>

      {error && <p className="text-xs text-red-500 mb-1">{error}</p>}
      {stats && (
        <p className="text-xs text-gray-400">
          Last run: {stats.rows_scanned?.toLocaleString()} rows scanned
          &nbsp;&mdash;&nbsp;{stats.keyword_matches} keyword matches
          &nbsp;&mdash;&nbsp;{stats.persisted} persisted, {stats.errors} errors
        </p>
      )}
      {status?.last_error && (
        <p className="text-xs text-red-400 mt-1">Last error: {status.last_error}</p>
      )}
    </div>
  )
}


function AlignmentCard() {
  const [forceApi, setForceApi] = useState(false)
  const [skipScored, setSkipScored] = useState(true)
  const [includeExpired, setIncludeExpired] = useState(true)
  const [profileId, setProfileId] = useState('all')
  const [profiles, setProfiles] = useState([])
  const [status, setStatus] = useState(null)
  const [error, setError] = useState('')
  const pollRef = useRef(null)

  const fetchStatus = async () => {
    try {
      const s = await getAlignStatus()
      setStatus(s)
      if (!s.running && pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    } catch {}
  }

  useEffect(() => {
    fetchStatus()
    getProfiles().then(setProfiles).catch(() => {})
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const handleRun = async () => {
    setError('')
    try {
      const params = { force_api: forceApi, skip_scored: skipScored, include_expired: includeExpired }
      if (profileId !== 'all') params.profile_id = Number(profileId)
      await runAlignment(params)
      pollRef.current = setInterval(fetchStatus, 3000)
      fetchStatus()
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to start alignment')
    }
  }

  const running = status?.running
  const stats = status?.last_stats

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
      <div className="flex items-start justify-between mb-1">
        <h3 className="font-semibold text-gray-900">Capability Alignment</h3>
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
          running ? 'bg-yellow-100 text-yellow-700' : 'bg-gray-100 text-gray-500'
        }`}>
          {running ? 'Running...' : 'Idle'}
        </span>
      </div>

      <p className="text-xs text-gray-500 mb-4">
        Score all solicitations against all capabilities using keyword matching + Claude semantic scoring.
      </p>

      <div className="flex flex-wrap items-center gap-4 mb-3">
        <div className="flex items-center gap-1.5">
          <label className="text-xs text-gray-500 whitespace-nowrap">Profile</label>
          <select
            value={profileId}
            onChange={e => setProfileId(e.target.value)}
            disabled={running}
            className="text-sm border border-gray-200 rounded px-2 py-1 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <option value="all">All profiles</option>
            {profiles.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={skipScored}
            onChange={e => setSkipScored(e.target.checked)}
            disabled={running || forceApi}
            className="rounded"
          />
          Skip already scored
        </label>
        <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={forceApi}
            onChange={e => { setForceApi(e.target.checked); if (e.target.checked) setSkipScored(false) }}
            disabled={running}
            className="rounded"
          />
          Force API (rescore everything)
        </label>
        <label className="flex items-center gap-1.5 text-xs text-gray-600 cursor-pointer select-none">
          <input
            type="checkbox"
            checked={includeExpired}
            onChange={e => setIncludeExpired(e.target.checked)}
            disabled={running}
            className="rounded"
          />
          Include expired
        </label>
        <button
          onClick={handleRun}
          disabled={running}
          className="px-4 py-1.5 bg-blue-700 text-white text-sm font-medium rounded hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Run Alignment
        </button>
      </div>

      {error && <p className="text-xs text-red-500 mb-1">{error}</p>}
      {stats && (
        <p className="text-xs text-gray-400">
          Last run: {stats.solicitations_scored} solicitations x {stats.capabilities} capabilities
          {' '}&mdash; {stats.api_calls_made} API calls, {stats.errors} errors
        </p>
      )}
      {status?.last_error && (
        <p className="text-xs text-red-400 mt-1">Last error: {status.last_error}</p>
      )}
    </div>
  )
}


function SchedulerCard() {
  const [info, setInfo] = useState(null)

  useEffect(() => {
    api.get('/config').then(r => setInfo(r.data.scheduler)).catch(() => {})
  }, [])

  if (!info) return null

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm p-5">
      <div className="flex items-start justify-between mb-1">
        <h3 className="font-semibold text-gray-900">Nightly Alignment</h3>
        <span className={`text-xs font-medium px-2 py-0.5 rounded ${
          info.enabled ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
        }`}>
          {info.enabled ? 'Scheduled' : 'Disabled'}
        </span>
      </div>
      {info.enabled ? (
        <p className="text-xs text-gray-500">
          Runs nightly at {String(info.hour).padStart(2,'0')}:{String(info.minute).padStart(2,'0')} server time.
          {info.next_run && <> Next run: {new Date(info.next_run).toLocaleString()}.</>}
          {' '}Skips already-scored pairs. Set <span className="font-mono">SCHEDULER_ENABLED=false</span> in .env to disable.
        </p>
      ) : (
        <p className="text-xs text-gray-500">
          Set <span className="font-mono">SCHEDULER_ENABLED=true</span> in .env to enable.
        </p>
      )}
    </div>
  )
}

export default function Admin() {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Admin</h1>
        <p className="text-sm text-gray-500 mt-1">
          Trigger data ingestion and scoring pipelines. Runs in the background — status updates every 3s.
        </p>
      </div>

      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Scrapers</h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        {SCRAPERS.map(cfg => <ScraperCard key={cfg.id} config={cfg} />)}
      </div>

      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">SAM.gov CSV Import</h2>
      <div className="max-w-xl mb-8">
        <SamCsvCard />
      </div>

      <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">Scoring</h2>
      <div className="max-w-xl space-y-4">
        <AlignmentCard />
        <SchedulerCard />
      </div>
    </div>
  )
}
