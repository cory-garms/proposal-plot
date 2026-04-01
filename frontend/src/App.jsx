import { BrowserRouter, Routes, Route } from 'react-router-dom'
import NavBar from './components/NavBar'
import SolicitationList from './views/SolicitationList'
import SolicitationDetail from './views/SolicitationDetail'
import DraftEditor from './views/DraftEditor'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <NavBar />
        <main>
          <Routes>
            <Route path="/" element={<SolicitationList />} />
            <Route path="/solicitations/:id" element={<SolicitationDetail />} />
            <Route path="/projects/:id" element={<DraftEditor />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
