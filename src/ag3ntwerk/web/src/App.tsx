import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { useStore } from './store'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Tasks from './pages/Tasks'
import Goals from './pages/Goals'
import COO from './pages/COO'
import Memory from './pages/Memory'
import Chat from './pages/Chat'
import Activity from './pages/Activity'
import Workflows from './pages/Workflows'
import Interviews from './pages/Interviews'
import ContentPipeline from './pages/ContentPipeline'

function NotFound() {
  return (
    <div className="flex flex-col items-center justify-center h-full p-8">
      <h1 className="text-4xl font-bold text-aw-text mb-2">404</h1>
      <p className="text-aw-muted mb-4">Page not found</p>
      <a href="/" className="text-aw-accent hover:underline">Return to Dashboard</a>
    </div>
  )
}

function App() {
  const { connect, fetchDashboardStats } = useStore()

  useEffect(() => {
    // Connect to WebSocket for real-time updates
    connect()

    // Initial data fetch
    fetchDashboardStats()

    // Periodic refresh
    const interval = setInterval(fetchDashboardStats, 30000)
    return () => clearInterval(interval)
  }, [connect, fetchDashboardStats])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="tasks" element={<Tasks />} />
          <Route path="goals" element={<Goals />} />
          <Route path="coo" element={<COO />} />
          <Route path="memory" element={<Memory />} />
          <Route path="chat" element={<Chat />} />
          <Route path="activity" element={<Activity />} />
          <Route path="workflows" element={<Workflows />} />
          <Route path="interviews" element={<Interviews />} />
          <Route path="content" element={<ContentPipeline />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
