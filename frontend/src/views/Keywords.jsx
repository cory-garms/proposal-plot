import { useState, useEffect, useMemo } from 'react'
import { getKeywords, createKeyword, toggleKeyword, deleteKeyword } from '../api/client'

const SOURCE_BADGE = {
  capability: 'bg-blue-100 text-blue-700',
  csv:        'bg-yellow-100 text-yellow-700',
  manual:     'bg-green-100 text-green-700',
}

export default function Keywords() {
  const [keywords, setKeywords] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [sourceFilter, setSourceFilter] = useState('all')
  const [activeFilter, setActiveFilter] = useState('all')
  const [newKeyword, setNewKeyword] = useState('')
  const [adding, setAdding] = useState(false)
  const [addError, setAddError] = useState('')

  useEffect(() => {
    getKeywords()
      .then(setKeywords)
      .catch(() => setError('Failed to load keywords'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = useMemo(() => {
    let kws = keywords
    if (activeFilter === 'active') kws = kws.filter(k => k.active)
    else if (activeFilter === 'inactive') kws = kws.filter(k => !k.active)
    if (sourceFilter !== 'all') kws = kws.filter(k => k.source === sourceFilter)
    const q = search.trim().toLowerCase()
    if (q) kws = kws.filter(k => k.keyword.includes(q))
    return kws
  }, [keywords, search, sourceFilter, activeFilter])

  const handleToggle = async (kw) => {
    // Optimistic
    setKeywords(prev => prev.map(k => k.id === kw.id ? { ...k, active: k.active ? 0 : 1 } : k))
    try {
      const updated = await toggleKeyword(kw.id, !kw.active)
      setKeywords(prev => prev.map(k => k.id === updated.id ? updated : k))
    } catch {
      // Revert
      setKeywords(prev => prev.map(k => k.id === kw.id ? kw : k))
    }
  }

  const handleDelete = async (kw) => {
    setKeywords(prev => prev.filter(k => k.id !== kw.id))
    try {
      await deleteKeyword(kw.id)
    } catch {
      setKeywords(prev => [...prev, kw].sort((a, b) => a.keyword.localeCompare(b.keyword)))
    }
  }

  const handleAdd = async (e) => {
    e.preventDefault()
    const kw = newKeyword.trim().toLowerCase()
    if (!kw) return
    setAdding(true)
    setAddError('')
    try {
      const created = await createKeyword(kw)
      setKeywords(prev =>
        prev.some(k => k.id === created.id) ? prev : [created, ...prev]
      )
      setNewKeyword('')
    } catch (err) {
      setAddError(err.response?.data?.detail || 'Failed to add keyword')
    } finally {
      setAdding(false)
    }
  }

  const activeCount = keywords.filter(k => k.active).length

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Search Keywords</h1>
          <p className="text-xs text-gray-500 mt-0.5">
            {activeCount} active &middot; {keywords.length} total
          </p>
        </div>
      </div>

      {/* Add keyword form */}
      <form onSubmit={handleAdd} className="bg-white border border-gray-200 rounded-lg shadow-sm p-4 mb-4 flex gap-2 items-start">
        <div className="flex-1">
          <input
            type="text"
            value={newKeyword}
            onChange={e => setNewKeyword(e.target.value)}
            placeholder="Add a keyword (e.g. synthetic aperture radar)"
            className="w-full text-sm border border-gray-200 rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          {addError && <p className="text-xs text-red-500 mt-1">{addError}</p>}
        </div>
        <button
          type="submit"
          disabled={adding || !newKeyword.trim()}
          className="px-4 py-2 bg-blue-700 text-white text-sm font-medium rounded hover:bg-blue-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors whitespace-nowrap"
        >
          {adding ? 'Adding...' : '+ Add'}
        </button>
      </form>

      {/* Filters */}
      <div className="bg-white border border-gray-200 rounded-lg shadow-sm px-4 py-3 mb-4 flex flex-wrap gap-3 items-center">
        <input
          type="text"
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search keywords..."
          className="text-sm border border-gray-200 rounded px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500 w-56"
        />
        <select
          value={sourceFilter}
          onChange={e => setSourceFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All sources</option>
          <option value="capability">Capability</option>
          <option value="csv">CSV</option>
          <option value="manual">Manual</option>
        </select>
        <select
          value={activeFilter}
          onChange={e => setActiveFilter(e.target.value)}
          className="text-sm border border-gray-200 rounded px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">Active + Inactive</option>
          <option value="active">Active only</option>
          <option value="inactive">Inactive only</option>
        </select>
        <span className="text-xs text-gray-400 ml-auto">{filtered.length} shown</span>
      </div>

      {/* Table */}
      {loading ? (
        <div className="text-center text-gray-400 py-12">Loading...</div>
      ) : error ? (
        <div className="text-center text-red-500 py-12">{error}</div>
      ) : filtered.length === 0 ? (
        <div className="text-center text-gray-400 py-12">No keywords match your filters.</div>
      ) : (
        <div className="bg-white border border-gray-200 rounded-lg shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide">Keyword</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide w-28">Source</th>
                <th className="text-left px-4 py-2.5 text-xs font-semibold text-gray-500 uppercase tracking-wide w-20">Active</th>
                <th className="px-4 py-2.5 w-16"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {filtered.map(kw => (
                <tr key={kw.id} className={`hover:bg-gray-50 transition-colors ${!kw.active ? 'opacity-50' : ''}`}>
                  <td className="px-4 py-2.5 font-mono text-gray-800">{kw.keyword}</td>
                  <td className="px-4 py-2.5">
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${SOURCE_BADGE[kw.source] || 'bg-gray-100 text-gray-600'}`}>
                      {kw.source}
                    </span>
                  </td>
                  <td className="px-4 py-2.5">
                    <button
                      onClick={() => handleToggle(kw)}
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors focus:outline-none ${
                        kw.active ? 'bg-blue-600' : 'bg-gray-300'
                      }`}
                      title={kw.active ? 'Deactivate' : 'Activate'}
                    >
                      <span className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
                        kw.active ? 'translate-x-4' : 'translate-x-1'
                      }`} />
                    </button>
                  </td>
                  <td className="px-4 py-2.5 text-right">
                    <button
                      onClick={() => handleDelete(kw)}
                      className="text-xs text-red-400 hover:text-red-600 transition-colors"
                      title="Delete"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
