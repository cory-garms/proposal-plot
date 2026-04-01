import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { getSolicitations, getAlignment, triggerScrape, getScrapeStatus } from '../api/client'

const SCORE_BADGE = (score) => {
  if (score === null || score === undefined) return 'bg-gray-100 text-gray-500'
  if (score >= 0.7) return 'bg-green-100 text-green-800'
  if (score >= 0.4) return 'bg-yellow-100 text-yellow-800'
  return 'bg-gray-100 text-gray-500'
}

export default function SolicitationList() {
  const navigate = useNavigate()
  const [solicitations, setSolicitations] = useState([])
  const [scores, setScores] = useState({})
  const [loading, setLoading] = useState(true)
  const [scraping, setScraping] = useState(false)
  const [scrapeMsg, setScrapeMsg] = useState('')
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const PAGE_SIZE = 25

  const fetchPage = useCallback(async (pageNum) => {
    setLoading(true)
    try {
      const data = await getSolicitations({ limit: PAGE_SIZE, offset: pageNum * PAGE_SIZE })
      setSolicitations(data)
      setHasMore(data.length === PAGE_SIZE)

      // Fetch top alignment score for each solicitation
      const scoreMap = {}
      await Promise.all(
        data.map(async (sol) => {
          try {
            const alignment = await getAlignment(sol.id)
            const top = alignment.scores?.[0]
            scoreMap[sol.id] = top ? { score: top.score, capability: top.capability } : null
          } catch {
            scoreMap[sol.id] = null
          }
        })
      )
      setScores(scoreMap)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchPage(page) }, [page, fetchPage])

  const handleScrape = async () => {
    setScraping(true)
    setScrapeMsg('Scrape started...')
    try {
      await triggerScrape({ max_pages: 5, enrich: true, max_detail: 50 })
      // Poll until done
      const poll = setInterval(async () => {
        const status = await getScrapeStatus()
        if (!status.running) {
          clearInterval(poll)
          setScraping(false)
          setScrapeMsg(`Done. ${status.last_count ?? 0} solicitations updated.`)
          fetchPage(0)
          setPage(0)
        }
      }, 2000)
    } catch (e) {
      setScraping(false)
      setScrapeMsg('Scrape failed: ' + (e.message || 'unknown error'))
    }
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">SBIR/STTR Solicitations</h1>
          <p className="text-sm text-gray-500 mt-1">{solicitations.length} loaded</p>
        </div>
        <div className="flex items-center gap-3">
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

      {loading ? (
        <div className="text-center py-16 text-gray-400">Loading solicitations...</div>
      ) : (
        <>
          <div className="bg-white border border-gray-200 rounded-lg overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 w-16">ID</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 w-24">Agency</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 w-28">Topic #</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600">Title</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 w-32">Deadline</th>
                  <th className="text-left px-4 py-3 font-semibold text-gray-600 w-44">Top Alignment</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {solicitations.map((sol) => {
                  const top = scores[sol.id]
                  return (
                    <tr
                      key={sol.id}
                      onClick={() => navigate(`/solicitations/${sol.id}`)}
                      className="hover:bg-blue-50 cursor-pointer transition-colors"
                    >
                      <td className="px-4 py-3 text-gray-400 font-mono">{sol.id}</td>
                      <td className="px-4 py-3 font-medium text-gray-700">{sol.agency}</td>
                      <td className="px-4 py-3 text-gray-500 font-mono text-xs">{sol.topic_number || '-'}</td>
                      <td className="px-4 py-3 text-gray-900">{sol.title}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{sol.deadline || '-'}</td>
                      <td className="px-4 py-3">
                        {top ? (
                          <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium ${SCORE_BADGE(top.score)}`}>
                            <span className="font-mono">{top.score.toFixed(2)}</span>
                            <span>{top.capability}</span>
                          </span>
                        ) : (
                          <span className="text-gray-300 text-xs">-</span>
                        )}
                      </td>
                    </tr>
                  )
                })}
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
