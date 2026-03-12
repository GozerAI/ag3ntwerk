import { Outlet, NavLink } from 'react-router-dom'
import { useStore } from '../store'
import {
  LayoutDashboard,
  ListTodo,
  Target,
  Brain,
  Database,
  MessageSquare,
  Activity,
  Mic,
  FileText,
  GitBranch,
  Wifi,
  WifiOff,
} from 'lucide-react'

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/activity', icon: Activity, label: 'Activity' },
  { to: '/tasks', icon: ListTodo, label: 'Tasks' },
  { to: '/goals', icon: Target, label: 'Goals' },
  { to: '/coo', icon: Brain, label: 'COO' },
  { to: '/interviews', icon: Mic, label: 'Interviews' },
  { to: '/content', icon: FileText, label: 'Content' },
  { to: '/workflows', icon: GitBranch, label: 'Workflows' },
  { to: '/memory', icon: Database, label: 'Memory' },
  { to: '/chat', icon: MessageSquare, label: 'Chat' },
]

export default function Layout() {
  const { connected, cooStatus } = useStore()

  const cooState = cooStatus?.state || 'unknown'
  const cooRunning = cooState !== 'idle' && cooState !== 'not_available' && cooState !== 'unknown'

  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 bg-csuite-surface border-r border-csuite-border flex flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-csuite-border">
          <h1 className="text-xl font-bold text-csuite-text">C-Suite</h1>
          <p className="text-sm text-csuite-muted">Command Center</p>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-4">
          <ul className="space-y-1">
            {navItems.map(({ to, icon: Icon, label }) => (
              <li key={to}>
                <NavLink
                  to={to}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors ${
                      isActive
                        ? 'bg-csuite-accent text-white'
                        : 'text-csuite-muted hover:text-csuite-text hover:bg-csuite-card'
                    }`
                  }
                >
                  <Icon size={20} />
                  <span>{label}</span>
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Status footer */}
        <div className="p-4 border-t border-csuite-border space-y-3">
          {/* Connection status */}
          <div className="flex items-center gap-2 text-sm">
            {connected ? (
              <>
                <Wifi size={16} className="text-csuite-success" />
                <span className="text-csuite-success">Connected</span>
              </>
            ) : (
              <>
                <WifiOff size={16} className="text-csuite-error" />
                <span className="text-csuite-error">Disconnected</span>
              </>
            )}
          </div>

          {/* COO status */}
          <div className="flex items-center gap-2 text-sm">
            <div
              className={`w-2 h-2 rounded-full ${
                cooRunning ? 'bg-csuite-success animate-pulse' : 'bg-csuite-muted'
              }`}
            />
            <span className="text-csuite-muted">
              COO: {cooRunning ? 'Running' : 'Idle'}
            </span>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 bg-csuite-bg overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
