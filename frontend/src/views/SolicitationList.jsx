import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSolicitations, triggerScrape, getScrapeStatus, watchSolicitation } from '../api/client'

const SCORE_BADGE = (score) => {
  if (score === null || score === undefined) return 'bg-gray-100 text-gray-500'
  if (score >= 0.7) return 'bg-green-100 text-green-800'
  if (score >= 0.4) return 'bg-yellow-100 text-yellow-800'
  return 'bg-gray-100 text-gray-500'
}

const renderAgency = (sol) => {
  const label = sol.branch || sol.agency || '-'
  const sub = sol.branch && sol.agency !== sol.branch ? sol.agency : null
  return (
    <div>
      <span className="font-medium text-gray-700">{label}</span>
      {sub && <div className="text-gray-400 text-xs">{sub}</div>}
    </div>
  )
}

const renderTpoc = (sol) => {
  let tpocs = []
  try { tpocs = JSON.parse(sol.tpoc_json || '[]') } catch {}
  if (!tpocs.length) return <span className="text-gray-300 text-xs">-</span>
  return (
    <div className="flex flex-col gap-0.5">
      {tpocs.slice(0, 2).map((t, i) => (
        <div key={i} className="text-xs">
          {t.email
            ? <a href={`mailto:${t.email}`} onClick={e => e.stopPropagation()} className="text-blue-600 hover:underline">{t.name}</a>
            : <span className="text-gray-600">{t.name}</span>
          }
        </div>
      ))}
    </div>
  )
}

const renderTiming = (sol) => {
  const closeDateStr = sol.close_date || sol.deadline
  if (!closeDateStr) return <span className="text-gray-300 text-xs">-</span>

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const close = new Date(closeDateStr)
  const open = sol.open_date ? new Date(sol.open_date) : null
  const daysUntilClose = Math.ceil((close - today) / (1000 * 60 * 60 * 24))

  let tags = []
  if (daysUntilClose < 0) {
    tags.push(<span key="expired" className="text-red-500 font-medium text-xs">Expired ({Math.abs(daysUntilClose)}d ago)</span>)
  } else if (daysUntilClose <= 7) {
    tags.push(<span key="closing" className="text-orange-600 font-medium text-xs bg-orange-50 px-1.5 py-0.5 rounded border border-orange-200">Closes in {daysUntilClose}d</span>)
  } else {
    tags.push(<span key="close" className="text-gray-500 text-xs">Closes in {daysUntilClose}d</span>)
  }

  if (open) {
    const daysUntilOpen = Math.ceil((open - today) / (1000 * 60 * 60 * 24))
    if (daysUntilOpen > 0 && daysUntilOpen <= 7) {
      tags.push(<span key="tpoc" className="text-blue-700 font-bold text-xs bg-blue-100 px-1.5 py-0.5 rounded border border-blue-200 mt-1">TPOC Window ({daysUntilOpen}d)</span>)
    } else if (daysUntilOpen > 7) {
      tags.push(<span key="tpoc" className="text-gray-400 text-xs mt-1">Pre-release ({daysUntilOpen}d)</span>)
    }
  }

  return <div className="flex flex-col items-start">{tags}</div>
}

export default function SolicitationList() {
  const navigate = useNavigate()
  const [solicitations, setSolicitations] = useState([])
  const [loading, setLoading] = useState(true)
  const [scraping, setScraping] = useState(false)
  const [scrapeMsg, setScrapeMsg] = useState('')
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [agencyFilter, setAgencyFilter] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [sortMode, setSortMode] = useState('alignmentDesc')
  const [savedTab, setSavedTab] = useState(false)
  const PAGE_SIZE = 25

  const fetchPage = useCallback(async (pageNum, agency, status, sort, saved) => {
    setLoading(true)
    try {
      const profileId = localStorage.getItem('profileId') || '1'
      const params = {
        limit: PAGE_SIZE,
        offset: pageNum * PAGE_SIZE,
        profile_id: profileId,
        exclude_expired: saved ? false : true,
      }
      if (agency) params.agency = agency
      if (status) params.status_filter = status
      if (saved) params.watched_only = true

      if (sort === 'deadlineAsc') { params.sort_by = 'deadline'; params.sort_desc = false }
      if (sort === 'deadlineDesc') { params.sort_by = 'deadline'; params.sort_desc = true }
      if (sort === 'alignmentDesc') { params.sort_by = 'alignment'; params.sort_desc = true }

      const data = await getSolicitations(params)
      setSolicitations(data)
      setHasMore(data.length === PAGE_SIZE)
    } catch (e) {
      console.error('Failed to fetch solicitations:', e)
      setSolicitations([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPage(page, agencyFilter, statusFilter, sortMode, savedTab)
  }, [page, agencyFilter, statusFilter, sortMode, savedTab, fetchPage])

  const handleWatch = async (e, sol) => {
    e.stopPropagation()
    const newVal = !sol.watched
    // Optimistic update
    setSolicitations(prev => prev.map(s => s.id === sol.id ? { ...s, watched: newVal ? 1 : 0 } : s))
    try {
      await watchSolicitation(sol.id, newVal)
      // If in Saved tab and unwatching, remove from list
      if (savedTab && !newVal) {
        setSolicitations(prev => prev.filter(s => s.id !== sol.id))
      }
    } catch (e) {
      // Revert on error
      setSolicitations(prev => prev.map(s => s.id === sol.id ? { ...s, watched: sol.watched } : s))
    }
  }

  const handleScrape = async () => {
    setScraping(true)
    setScrapeMsg('Scrape started...')
    try {
      await triggerScrape({ max_pages: 5, enrich: true, max_detail: 50 })
      const poll = setInterval(async () => {
        const status = await getScrapeStatus()
        if (!status.running) {
          clearInterval(poll)
          setScraping(false)
          setScrapeMsg(`Done. ${status.last_count ?? 0} solicitations updated.`)
          fetchPage(0, agencyFilter, statusFilter, sortMode, savedTab)
          setPage(0)
        }
      }, 2000)
    } catch (e) {
      setScraping(false)
      setScrapeMsg('Scrape failed: ' + (e.message || 'unknown error'))
    }
  }

  const resetFilters = () => {
    setPage(0)
    setAgencyFilter('')
    setStatusFilter('')
    setSortMode('')
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Solicitations</h1>
          <p className="text-sm text-gray-500 mt-1">{solicitations.length} loaded</p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(0) }}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Statuses</option>
            <option value="tpoc">TPOC Window</option>
            <option value="open">Open Now</option>
            <option value="closing">Closing Soon</option>
            <option value="expired">Expired</option>
          </select>
          <select
            value={sortMode}
            onChange={(e) => { setSortMode(e.target.value); setPage(0) }}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">Newest Scraped</option>
            <option value="alignmentDesc">Top Alignment</option>
            <option value="deadlineAsc">Deadline (Soonest)</option>
            <option value="deadlineDesc">Deadline (Latest)</option>
          </select>
          <select
            value={agencyFilter}
            onChange={(e) => { setAgencyFilter(e.target.value); setPage(0) }}
            className="border border-gray-300 rounded px-3 py-1.5 text-sm outline-none focus:ring-1 focus:ring-blue-500"
          >
            <option value="">All Agencies</option>
            <option value="DOD">DOD</option>
            <option value="DARPA">DARPA</option>
            <option value="NASA">NASA</option>
            <option value="NSF">NSF</option>
            <option value="NIH">NIH</option>
            <option value="USDA">USDA</option>
            <option value="DOE">DOE</option>
            <option value="NOAA">NOAA</option>
            <option value="DOI">DOI</option>
          </select>
          {scrapeMsg && <span className="text-sm text-gray-600">{scrapeMsg}</span>}
          <button
            onClick={handleScrape}
            disabled={scraping}
            className="px-4 py-2 bg-blue-700 text-white text-sm rounded hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {scraping ? 'Scraping...' : 'Scrape New'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-4 border-b border-gray-200">
        <button
          onClick={() => { setSavedTab(false); resetFilters() }}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            !savedTab ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          All
        </button>
        <button
          onClick={() => { setSavedTab(true); resetFilters() }}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
            savedTab ? 'border-blue-600 text-blue-700' : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          <span>&#9733;</span> Saved
        </button>
      </div>

      {loading ? (
        <div className="text-center py-16 text-gray-400">Loading solicitations...</div>
      ) : solicitations.length === 0 ? (
        <div className="text-center py-16 text-gray-400">
          {savedTab ? 'No saved solicitations. Click the star on any row to save it.' : 'No solicitations found.'}
        </div>
      ) : (
        <>
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-3 py-3 w-8"></th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 w-28">Agency / Branch</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 w-28">Topic #</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Title</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 w-36">TPOC</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 w-32">Deadline</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 w-44">Top Alignment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {solicitations.map((sol) => (
                  <tr
                    key={sol.id}
                    onClick={() => navigate(`/solicitations/${sol.id}`)}
                    className="hover:bg-blue-50 cursor-pointer transition-colors"
                  >
                    <td className="px-3 py-3" onClick={(e) => handleWatch(e, sol)}>
                      <span
                        title={sol.watched ? 'Remove from saved' : 'Save this solicitation'}
                        className={`text-lg leading-none cursor-pointer select-none transition-colors ${
                          sol.watched ? 'text-yellow-400 hover:text-yellow-500' : 'text-gray-200 hover:text-yellow-300'
                        }`}
                      >
                        &#9733;
                      </span>
                    </td>
                    <td className="px-4 py-3">{renderAgency(sol)}</td>
                    <td className="px-4 py-3 text-gray-500 font-mono text-xs">{sol.topic_number || '-'}</td>
                    <td className="px-4 py-3 text-gray-900">{sol.title}</td>
                    <td className="px-4 py-3">{renderTpoc(sol)}</td>
                    <td className="px-4 py-3">{renderTiming(sol)}</td>
                    <td className="px-4 py-3">
                      {sol.top_alignment_score !== null && sol.top_alignment_score !== undefined ? (
                        <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium ${SCORE_BADGE(sol.top_alignment_score)}`}>
                          <span className="font-mono">{sol.top_alignment_score.toFixed(2)}</span>
                          <span>{sol.top_capability}</span>
                        </span>
                      ) : (
                        <span className="text-gray-300 text-xs">-</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex justify-between items-center mt-4">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-3 py-1.5 text-sm border rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Previous
            </button>
            <span className="text-sm text-gray-500">Page {page + 1}</span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={!hasMore}
              className="px-3 py-1.5 text-sm border rounded disabled:opacity-40 hover:bg-gray-50"
            >
              Next
            </button>
          </div>
        </>
      )}
    </div>
  )
}
