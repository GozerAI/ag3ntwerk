import { useEffect, useState } from 'react'
import { useStore } from '../store'
import {
  Activity as ActivityIcon,
  Brain,
  Target,
  CheckCircle,
  Clock,
  AlertCircle,
  TrendingUp,
  Zap,
  RefreshCw,
  ChevronRight,
  Play,
  Pause,
} from 'lucide-react'

interface ActivityItem {
  id: string
  type: string
  title: string
  description: string
  executive?: string
  timestamp: string
  status: 'completed' | 'running' | 'pending' | 'failed'
  result?: string
}

export default function Activity() {
  const {
    cooStatus,
    fetchCOOStatus,
    goals,
    fetchGoals,
    tasks,
    fetchTasks,
    startCOO,
    stopCOO,
    activities,
    dashboardStats,
    fetchDashboardStats,
  } = useStore()

  const [recentActivity, setRecentActivity] = useState<ActivityItem[]>([])

  useEffect(() => {
    fetchCOOStatus()
    fetchGoals()
    fetchTasks()
    fetchDashboardStats()
    const interval = setInterval(() => {
      fetchCOOStatus()
      fetchTasks()
      fetchDashboardStats()
    }, 5000)
    return () => clearInterval(interval)
  }, [fetchCOOStatus, fetchGoals, fetchTasks, fetchDashboardStats])

  useEffect(() => {
    // Convert tasks and websocket activities into a unified activity feed
    const taskActivities: ActivityItem[] = tasks
      .slice(0, 10)
      .map((task) => ({
        id: task.id,
        type: 'task',
        title: task.description.slice(0, 60) + (task.description.length > 60 ? '...' : ''),
        description: task.task_type,
        executive: task.routed_to,
        timestamp: task.created_at || new Date().toISOString(),
        status: task.status as ActivityItem['status'],
        result: typeof task.result === 'string' ? task.result : undefined,
      }))

    setRecentActivity(taskActivities)
  }, [tasks, activities])

  const isRunning =
    cooStatus?.state &&
    cooStatus.state !== 'idle' &&
    cooStatus.state !== 'not_available' &&
    cooStatus.state !== 'unknown'

  const activeGoals = goals.filter((g) => g.status !== 'completed' && g.status !== 'abandoned')
  const pendingTasks = tasks.filter((t) => t.status === 'pending')
  const runningTasks = tasks.filter((t) => t.status === 'running')
  const completedTasks = tasks.filter((t) => t.status === 'completed')

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-aw-text">System Activity</h1>
          <p className="text-aw-muted mt-1">
            Autonomous operations dashboard - observe what the system is doing
          </p>
        </div>
        <button
          onClick={() => {
            fetchCOOStatus()
            fetchTasks()
            fetchGoals()
          }}
          className="flex items-center gap-2 px-4 py-2 text-aw-muted hover:text-aw-text transition-colors"
        >
          <RefreshCw size={20} />
          Refresh
        </button>
      </div>

      {/* COO Status Banner */}
      <div
        className={`rounded-xl border p-6 mb-8 ${
          isRunning
            ? 'bg-aw-success/10 border-aw-success/30'
            : 'bg-aw-surface border-aw-border'
        }`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div
              className={`p-4 rounded-xl ${
                isRunning ? 'bg-aw-success/20' : 'bg-aw-card'
              }`}
            >
              <Brain
                size={32}
                className={isRunning ? 'text-aw-success' : 'text-aw-muted'}
              />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-aw-text">
                CoS (Overwatch) - {isRunning ? 'Active' : 'Idle'}
              </h2>
              <p className="text-aw-muted">
                Mode: <span className="font-medium">{cooStatus?.mode || 'supervised'}</span>
                {cooStatus?.state && cooStatus.state !== 'idle' && (
                  <span className="ml-3">
                    State: <span className="font-medium">{cooStatus.state}</span>
                  </span>
                )}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="text-right">
              <p className="text-2xl font-bold text-aw-text">
                {cooStatus?.successful_executions || 0}
              </p>
              <p className="text-sm text-aw-muted">tasks completed</p>
            </div>
            <button
              onClick={isRunning ? stopCOO : startCOO}
              className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors ${
                isRunning
                  ? 'bg-aw-warning hover:bg-yellow-600 text-white'
                  : 'bg-aw-success hover:bg-green-600 text-white'
              }`}
            >
              {isRunning ? (
                <>
                  <Pause size={20} />
                  Pause
                </>
              ) : (
                <>
                  <Play size={20} />
                  Activate
                </>
              )}
            </button>
          </div>
        </div>

        {/* Current activity indicator */}
        {runningTasks.length > 0 && (
          <div className="mt-4 pt-4 border-t border-aw-success/20">
            <div className="flex items-center gap-2 text-aw-success">
              <Zap size={16} className="animate-pulse" />
              <span className="text-sm font-medium">Currently executing:</span>
              <span className="text-sm">{runningTasks[0].description}</span>
            </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Goal Progress - Left Column */}
        <div className="lg:col-span-2 space-y-6">
          {/* Strategic Goals */}
          <section className="bg-aw-surface rounded-xl border border-aw-border p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-aw-text flex items-center gap-2">
                <Target size={20} className="text-aw-accent" />
                Strategic Goals
              </h2>
              <span className="text-sm text-aw-muted">
                {activeGoals.length} active
              </span>
            </div>

            {activeGoals.length > 0 ? (
              <div className="space-y-4">
                {activeGoals.slice(0, 5).map((goal) => {
                  const completedMilestones =
                    goal.milestones?.filter((m) => m.status === 'completed').length || 0
                  const totalMilestones = goal.milestones?.length || 0
                  const progress =
                    totalMilestones > 0
                      ? (completedMilestones / totalMilestones) * 100
                      : goal.progress

                  return (
                    <div key={goal.id} className="bg-aw-card rounded-lg p-4">
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-medium text-aw-text">{goal.title}</h3>
                        <span className="text-sm text-aw-muted">
                          {completedMilestones}/{totalMilestones}
                        </span>
                      </div>
                      {goal.description && (
                        <p className="text-sm text-aw-muted mb-3 line-clamp-2">
                          {goal.description}
                        </p>
                      )}
                      <div className="flex items-center gap-3">
                        <div className="flex-1 h-2 bg-aw-surface rounded-full overflow-hidden">
                          <div
                            className="h-full bg-aw-accent rounded-full transition-all"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                        <span className="text-xs text-aw-muted w-12 text-right">
                          {progress.toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="text-center py-8">
                <Target size={48} className="mx-auto mb-2 text-aw-muted opacity-50" />
                <p className="text-aw-muted">No active goals</p>
              </div>
            )}
          </section>

          {/* Activity Feed */}
          <section className="bg-aw-surface rounded-xl border border-aw-border p-6">
            <h2 className="text-lg font-semibold text-aw-text flex items-center gap-2 mb-4">
              <ActivityIcon size={20} className="text-aw-accent" />
              Recent Activity
            </h2>

            {recentActivity.length > 0 ? (
              <div className="space-y-3">
                {recentActivity.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-start gap-3 bg-aw-card rounded-lg p-3"
                  >
                    {activity.status === 'completed' ? (
                      <CheckCircle size={18} className="text-aw-success mt-0.5" />
                    ) : activity.status === 'running' ? (
                      <Clock size={18} className="text-aw-accent animate-pulse mt-0.5" />
                    ) : activity.status === 'failed' ? (
                      <AlertCircle size={18} className="text-aw-error mt-0.5" />
                    ) : (
                      <Clock size={18} className="text-aw-muted mt-0.5" />
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-aw-text">{activity.title}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-aw-muted">{activity.description}</span>
                        {activity.executive && (
                          <>
                            <span className="text-aw-border">|</span>
                            <span className="text-xs text-aw-accent">{activity.executive}</span>
                          </>
                        )}
                      </div>
                      {activity.result && activity.status === 'completed' && (
                        <p className="text-xs text-aw-muted mt-2 line-clamp-2 bg-aw-surface p-2 rounded">
                          {activity.result.slice(0, 150)}
                          {activity.result.length > 150 ? '...' : ''}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <ActivityIcon size={48} className="mx-auto mb-2 text-aw-muted opacity-50" />
                <p className="text-aw-muted">No recent activity</p>
                <p className="text-sm text-aw-muted mt-1">
                  Create a task or goal to see activity here
                </p>
              </div>
            )}
          </section>
        </div>

        {/* Right Column - Stats & Queue */}
        <div className="space-y-6">
          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-3">
            <StatCard
              icon={CheckCircle}
              label="Completed"
              value={completedTasks.length}
              color="success"
            />
            <StatCard
              icon={Clock}
              label="Pending"
              value={pendingTasks.length}
              color="warning"
            />
            <StatCard
              icon={Target}
              label="Goals"
              value={activeGoals.length}
              color="accent"
            />
            <StatCard
              icon={TrendingUp}
              label="Success Rate"
              value={`${dashboardStats?.tasks?.completed && dashboardStats?.tasks?.total
                ? ((dashboardStats.tasks.completed / dashboardStats.tasks.total) * 100).toFixed(0)
                : 0}%`}
              color="success"
            />
          </div>

          {/* Task Queue */}
          <section className="bg-aw-surface rounded-xl border border-aw-border p-6">
            <h2 className="text-lg font-semibold text-aw-text flex items-center gap-2 mb-4">
              <Clock size={20} className="text-aw-warning" />
              Task Queue
            </h2>

            {pendingTasks.length > 0 ? (
              <div className="space-y-2">
                {pendingTasks.slice(0, 5).map((task, index) => (
                  <div
                    key={task.id}
                    className="flex items-center gap-3 bg-aw-card rounded-lg p-3"
                  >
                    <span className="w-6 h-6 rounded-full bg-aw-warning/20 text-aw-warning flex items-center justify-center text-xs font-medium">
                      {index + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-aw-text truncate">{task.description}</p>
                      <p className="text-xs text-aw-muted">{task.task_type}</p>
                    </div>
                    <ChevronRight size={16} className="text-aw-muted" />
                  </div>
                ))}
                {pendingTasks.length > 5 && (
                  <p className="text-xs text-aw-muted text-center pt-2">
                    +{pendingTasks.length - 5} more in queue
                  </p>
                )}
              </div>
            ) : (
              <div className="text-center py-6">
                <CheckCircle size={32} className="mx-auto mb-2 text-aw-success opacity-50" />
                <p className="text-sm text-aw-muted">Queue is empty</p>
              </div>
            )}
          </section>

          {/* System Mode Info */}
          <section className="bg-aw-surface rounded-xl border border-aw-border p-6">
            <h2 className="text-lg font-semibold text-aw-text mb-4">Operating Mode</h2>
            <div className="space-y-3">
              <ModeIndicator
                label="Supervised"
                description="Execute but report all actions"
                active={cooStatus?.mode === 'supervised'}
              />
              <ModeIndicator
                label="Autonomous"
                description="Full autonomous operation"
                active={cooStatus?.mode === 'autonomous'}
              />
              <ModeIndicator
                label="Approval"
                description="Request approval for each action"
                active={cooStatus?.mode === 'approval'}
              />
            </div>
            <p className="text-xs text-aw-muted mt-4">
              Change mode in the COO settings
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
}: {
  icon: React.ElementType
  label: string
  value: string | number
  color: 'success' | 'warning' | 'error' | 'accent'
}) {
  const colorMap = {
    success: 'text-aw-success',
    warning: 'text-aw-warning',
    error: 'text-aw-error',
    accent: 'text-aw-accent',
  }

  return (
    <div className="bg-aw-surface rounded-xl border border-aw-border p-4">
      <div className="flex items-center gap-2 text-aw-muted mb-1">
        <Icon size={14} />
        <span className="text-xs">{label}</span>
      </div>
      <p className={`text-xl font-bold ${colorMap[color]}`}>{value}</p>
    </div>
  )
}

function ModeIndicator({
  label,
  description,
  active,
}: {
  label: string
  description: string
  active: boolean
}) {
  return (
    <div
      className={`p-3 rounded-lg border transition-colors ${
        active
          ? 'border-aw-accent bg-aw-accent/10'
          : 'border-aw-border bg-aw-card'
      }`}
    >
      <p className={`text-sm font-medium ${active ? 'text-aw-accent' : 'text-aw-muted'}`}>
        {label}
      </p>
      <p className="text-xs text-aw-muted">{description}</p>
    </div>
  )
}
