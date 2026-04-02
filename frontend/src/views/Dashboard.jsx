import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getDashboard } from '../api/client'

export default function Dashboard() {
  const navigate = useNavigate()
  const [data, setData] = useState({
    tpoc_window: [],
    newly_released: [],
    open_now: [],
    closing_soon: [],
    recently_closed: [],
    coming_soon: []
  })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="p-8 text-center text-gray-400">Loading Dashboard...</div>

  const Section = ({ title, items, isSchedule = false, icon, colorClass }) => {
    if (!items || items.length === 0) return null;
    
    return (
      <div className="mb-8">
        <div className="flex items-center gap-2 mb-4">
          <span className={`text-xl ${colorClass}`}>{icon}</span>
          <h2 className="text-lg font-bold text-gray-800">{title} <span className="text-sm font-normal text-gray-400 ml-2">({items.length})</span></h2>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {items.map((item, idx) => {
            if (isSchedule) {
              return (
                <div key={idx} className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm hover:shadow transition-shadow">
                  <div className="flex justify-between items-start mb-2">
                    <span className="bg-blue-100 text-blue-800 text-xs font-semibold px-2 py-0.5 rounded uppercase">{item.agency}</span>
                    <span className="text-gray-500 text-xs font-medium">{item.solicitation_cycle}</span>
                  </div>
                  <div className="mt-3 text-sm text-gray-700">
                    <p className="mb-1"><span className="font-semibold text-gray-900">Expected Release:</span> {item.expected_release_month}</p>
                    <p><span className="font-semibold text-gray-900">Expected Open:</span> {item.expected_open_month}</p>
                  </div>
                  {item.notes && <p className="mt-3 text-xs text-gray-500 italic border-t border-gray-100 pt-2">{item.notes}</p>}
                </div>
              );
            }
            return (
              <div 
                key={item.id} 
                className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm hover:shadow-md transition-all cursor-pointer hover:border-blue-300"
                onClick={() => navigate(`/solicitations/${item.id}`)}
              >
                <div className="flex justify-between items-start mb-2">
                  <span className="bg-gray-100 text-gray-800 text-xs font-semibold px-2 py-0.5 rounded">{item.agency}</span>
                  <span className="text-gray-500 font-mono text-xs">{item.topic_number || '-'}</span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2 line-clamp-2 text-sm leading-snug">{item.title}</h3>
                <div className="flex flex-col gap-1 mt-auto">
                  {item.open_date && <span className="text-xs text-gray-500">Opens: {item.open_date}</span>}
                  {(item.close_date || item.deadline) && <span className="text-xs text-gray-500">Closes: {item.close_date || item.deadline}</span>}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Agency Release Calendar</h1>
        <p className="text-sm text-gray-500 mt-1">Proactive tracking of SBIR/STTR topics across their lifecycle</p>
      </div>

      <Section title="Action Required: TPOC Window Active" items={data.tpoc_window} icon="🚨" colorClass="text-red-600" />
      <Section title="Closing Soon (< 30 days)" items={data.closing_soon} icon="⏳" colorClass="text-orange-500" />
      <Section title="Open Now (active)" items={data.open_now} icon="🟢" colorClass="text-green-500" />
      <Section title="Newly Released (last 14 days)" items={data.newly_released} icon="⭐" colorClass="text-yellow-500" />
      <Section title="Coming Soon (Expected Cycles)" items={data.coming_soon} isSchedule={true} icon="📅" colorClass="text-blue-500" />
      <Section title="Recently Closed" items={data.recently_closed} icon="🔒" colorClass="text-gray-400" />
    </div>
  )
}
