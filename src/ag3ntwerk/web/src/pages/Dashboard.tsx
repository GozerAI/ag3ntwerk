import { useEffect } from 'react'
import { useStore } from '../store'
import { Link } from 'react-router-dom'
import {
  ListTodo,
  Target,
  Brain,
  Database,
  Lightbulb,
  Activity,
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

export default function Dashboard() {
  const { dashboardStats, cooStatus, activities, fetchDashboardStats } = useStore()

  useEffect(() => {
    fetchDashboardStats()
  }, [fetchDashboardStats])

  const stats = dashboardStats || {
    tasks: { total: 0, active: 0, completed: 0 },
    goals: { total: 0, active: 0 },
    memory: { total_chunks: 0 },
    knowledge: { total_entities: 0, total_facts: 0 },
    decisions: { total: 0 },
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-aw-text">Command Center</h1>
        <p className="text-aw-muted mt-1">Your unified dashboard for all affairs</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={ListTodo}
          label="Active Tasks"
          value={stats.tasks.active}
          subtext={`${stats.tasks.completed} completed`}
          href="/tasks"
          color="accent"
        />
        <StatCard
          icon={Target}
          label="Active Goals"
          value={stats.goals.active}
          subtext={`${stats.goals.total} total`}
          href="/goals"
          color="success"
        />
        <StatCard
          icon={Database}
          label="Memory Chunks"
          value={stats.memory.total_chunks || 0}
          subtext={`${stats.knowledge.total_entities || 0} entities`}
          href="/memory"
          color="warning"
        />
        <StatCard
          icon={Lightbulb}
          label="Decisions"
          value={stats.decisions.total}
          subtext={`${stats.knowledge.total_facts || 0} facts`}
          href="/memory"
          color="error"
        />
      </div>

      {/* COO Status & Activity Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* COO Status Card */}
        <div className="lg:col-span-2 bg-aw-surface rounded-xl border border-aw-border p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-aw-text flex items-center gap-2">
              <Brain size={24} className="text-aw-accent" />
              COO Status
            </h2>
            <Link
              to="/coo"
              className="text-sm text-aw-accent hover:underline"
            >
              View Details →
            </Link>
          </div>

          {cooStatus ? (
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <COOMetric
                icon={Activity}
                label="State"
                value={cooStatus.state || 'unknown'}
                isState
              />
              <COOMetric
                icon={Brain}
                label="Codename"
                value={cooStatus.codename || 'Nexus'}
              />
              <COOMetric
                icon={ListTodo}
                label="Tasks Executed"
                value={String(cooStatus.total_tasks_executed || 0)}
              />
            </div>
          ) : (
            <div className="text-center py-8 text-aw-muted">
              <Brain size={48} className="mx-auto mb-2 opacity-50" />
              <p>COO not initialized</p>
            </div>
          )}

          {/* COO Actions */}
          <div className="mt-6 flex gap-3">
            <COOActionButton />
          </div>
        </div>

        {/* Activity Feed */}
        <div className="bg-aw-surface rounded-xl border border-aw-border p-6">
          <h2 className="text-xl font-semibold text-aw-text mb-4">Activity Feed</h2>
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {activities.length > 0 ? (
              activities.slice(0, 10).map((activity, i) => (
                <ActivityItem key={i} activity={activity} />
              ))
            ) : (
              <p className="text-aw-muted text-center py-8">
                No recent activity
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  subtext,
  href,
  color,
}: {
  icon: React.ElementType
  label: string
  value: number | string
  subtext: string
  href: string
  color: 'accent' | 'success' | 'warning' | 'error'
}) {
  const colorMap = {
    accent: 'text-aw-accent',
    success: 'text-aw-success',
    warning: 'text-aw-warning',
    error: 'text-aw-error',
  }

  return (
    <Link
      to={href}
      className="bg-aw-surface rounded-xl border border-aw-border p-6 hover:border-aw-accent transition-colors"
    >
      <div className="flex items-center gap-4">
        <div className={`p-3 rounded-lg bg-aw-card ${colorMap[color]}`}>
          <Icon size={24} />
        </div>
        <div>
          <p className="text-3xl font-bold text-aw-text">{value}</p>
          <p className="text-sm text-aw-muted">{label}</p>
          <p className="text-xs text-aw-muted mt-1">{subtext}</p>
        </div>
      </div>
    </Link>
  )
}

function COOMetric({
  icon: Icon,
  label,
  value,
  isState,
}: {
  icon: React.ElementType
  label: string
  value: string
  isState?: boolean
}) {
  const stateColors: Record<string, string> = {
    idle: 'text-aw-muted',
    observing: 'text-aw-success',
    prioritizing: 'text-aw-accent',
    delegating: 'text-aw-warning',
    executing: 'text-aw-success',
    learning: 'text-aw-accent',
    waiting_approval: 'text-aw-warning',
  }

  return (
    <div className="bg-aw-card rounded-lg p-4">
      <div className="flex items-center gap-2 text-aw-muted mb-1">
        <Icon size={16} />
        <span className="text-sm">{label}</span>
      </div>
      <p
        className={`text-lg font-semibold ${
          isState ? stateColors[value] || 'text-aw-text' : 'text-aw-text'
        }`}
      >
        {value}
      </p>
    </div>
  )
}

function COOActionButton() {
  const { cooStatus, startCOO, stopCOO } = useStore()

  const isRunning =
    cooStatus?.state &&
    cooStatus.state !== 'idle' &&
    cooStatus.state !== 'not_available' &&
    cooStatus.state !== 'unknown'

  const handleClick = async () => {
    if (isRunning) {
      await stopCOO()
    } else {
      await startCOO()
    }
  }

  return (
    <button
      onClick={handleClick}
      className={`px-6 py-2 rounded-lg font-medium transition-colors ${
        isRunning
          ? 'bg-aw-error hover:bg-red-600 text-white'
          : 'bg-aw-success hover:bg-green-600 text-white'
      }`}
    >
      {isRunning ? 'Stop COO' : 'Start COO'}
    </button>
  )
}

function ActivityItem({ activity }: { activity: { type: string; data: unknown; timestamp: string } }) {
  const typeLabels: Record<string, string> = {
    task_created: 'Task created',
    task_updated: 'Task updated',
    task_completed: 'Task completed',
    goal_created: 'Goal created',
    coo_started: 'COO started',
    coo_stopped: 'COO stopped',
    connected: 'Connected',
  }

  const typeColors: Record<string, string> = {
    task_created: 'bg-aw-accent',
    task_completed: 'bg-aw-success',
    goal_created: 'bg-aw-warning',
    coo_started: 'bg-aw-success',
    coo_stopped: 'bg-aw-error',
    connected: 'bg-aw-muted',
  }

  return (
    <div className="flex items-center gap-3">
      <div className={`w-2 h-2 rounded-full ${typeColors[activity.type] || 'bg-aw-muted'}`} />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-aw-text truncate">
          {typeLabels[activity.type] || activity.type}
        </p>
        <p className="text-xs text-aw-muted">
          {formatDistanceToNow(new Date(activity.timestamp), { addSuffix: true })}
        </p>
      </div>
    </div>
  )
}

