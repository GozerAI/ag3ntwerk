import { useEffect, useState } from 'react'
import { useStore } from '../store'
import { Plus, Check, Clock, XCircle, Loader2, ChevronDown } from 'lucide-react'

const TASK_TYPES = [
  { value: 'general', label: 'General' },
  { value: 'security_review', label: 'Security Review (CIO)' },
  { value: 'code_review', label: 'Code Review (CTO)' },
  { value: 'market_analysis', label: 'Market Analysis (CSO)' },
  { value: 'data_analysis', label: 'Data Analysis (CDO)' },
  { value: 'content_creation', label: 'Content Creation (CMO)' },
  { value: 'strategic_planning', label: 'Strategic Planning (CSO)' },
  { value: 'financial_analysis', label: 'Financial Analysis (CFO)' },
]

export default function Tasks() {
  const { tasks, fetchTasks, createTask, cooStatus } = useStore()
  const [showCreate, setShowCreate] = useState(false)
  const [newDescription, setNewDescription] = useState('')
  const [newTaskType, setNewTaskType] = useState('general')
  const [newPriority, setNewPriority] = useState('medium')
  const [creating, setCreating] = useState(false)

  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  const handleCreate = async () => {
    if (!newDescription.trim()) return
    setCreating(true)
    await createTask({
      description: newDescription,
      task_type: newTaskType,
      priority: newPriority,
    })
    setNewDescription('')
    setNewTaskType('general')
    setNewPriority('medium')
    setShowCreate(false)
    setCreating(false)
  }

  const activeTasks = tasks.filter((t) => t.status !== 'completed' && t.status !== 'failed')
  const completedTasks = tasks.filter((t) => t.status === 'completed')
  const failedTasks = tasks.filter((t) => t.status === 'failed')

  const cooReady = cooStatus?.state && cooStatus.state !== 'idle' && cooStatus.state !== 'not_available' && cooStatus.state !== 'unknown'

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-aw-text">Tasks</h1>
          <p className="text-aw-muted mt-1">
            {activeTasks.length} active, {completedTasks.length} completed
            {!cooReady && ' (COO offline - tasks won\'t execute)'}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-aw-accent text-white rounded-lg hover:bg-indigo-600 transition-colors"
        >
          <Plus size={20} />
          New Task
        </button>
      </div>

      {/* Create Task Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-aw-surface rounded-xl border border-aw-border p-6 w-full max-w-lg">
            <h2 className="text-xl font-semibold text-aw-text mb-4">Create Task</h2>
            <textarea
              placeholder="Describe what you want to accomplish..."
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              className="w-full bg-aw-card border border-aw-border rounded-lg px-4 py-3 text-aw-text mb-3 h-32 resize-none"
              autoFocus
            />
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div>
                <label className="block text-sm text-aw-muted mb-1">Task Type</label>
                <select
                  value={newTaskType}
                  onChange={(e) => setNewTaskType(e.target.value)}
                  className="w-full bg-aw-card border border-aw-border rounded-lg px-4 py-2 text-aw-text"
                >
                  {TASK_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm text-aw-muted mb-1">Priority</label>
                <select
                  value={newPriority}
                  onChange={(e) => setNewPriority(e.target.value)}
                  className="w-full bg-aw-card border border-aw-border rounded-lg px-4 py-2 text-aw-text"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>
            {!cooReady && (
              <div className="mb-4 p-3 bg-aw-warning/10 border border-aw-warning/30 rounded-lg text-sm text-aw-warning">
                COO is not connected. Task will be created but won't execute automatically.
              </div>
            )}
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 text-aw-muted hover:text-aw-text"
                disabled={creating}
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={creating || !newDescription.trim()}
                className="px-4 py-2 bg-aw-accent text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50 flex items-center gap-2"
              >
                {creating && <Loader2 size={16} className="animate-spin" />}
                {creating ? 'Creating...' : 'Create & Execute'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Active Tasks */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-aw-text mb-4">Active Tasks</h2>
        <div className="space-y-3">
          {activeTasks.length > 0 ? (
            activeTasks.map((task) => (
              <TaskCard key={task.id} task={task} />
            ))
          ) : (
            <div className="bg-aw-surface rounded-xl border border-aw-border p-8 text-center">
              <p className="text-aw-muted">No active tasks</p>
              <button
                onClick={() => setShowCreate(true)}
                className="mt-2 text-aw-accent hover:underline"
              >
                Create your first task
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Completed Tasks */}
      {completedTasks.length > 0 && (
        <section className="mb-8">
          <h2 className="text-lg font-semibold text-aw-text mb-4">Completed</h2>
          <div className="space-y-3">
            {completedTasks.slice(0, 10).map((task) => (
              <TaskCard key={task.id} task={task} />
            ))}
          </div>
        </section>
      )}

      {/* Failed Tasks */}
      {failedTasks.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-aw-text mb-4">Failed</h2>
          <div className="space-y-3">
            {failedTasks.slice(0, 5).map((task) => (
              <TaskCard key={task.id} task={task} />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function TaskCard({ task }: { task: {
  id: string
  description: string
  task_type: string
  status: string
  priority: string
  result?: string | { content?: string; [key: string]: unknown }
  routed_to?: string
}}) {
  const [expanded, setExpanded] = useState(false)

  const priorityColors: Record<string, string> = {
    low: 'border-l-aw-muted',
    medium: 'border-l-aw-accent',
    high: 'border-l-aw-warning',
    critical: 'border-l-aw-error',
  }

  const statusIcons: Record<string, React.ReactNode> = {
    pending: <Clock size={16} className="text-aw-muted" />,
    running: <Loader2 size={16} className="text-aw-accent animate-spin" />,
    completed: <Check size={16} className="text-aw-success" />,
    failed: <XCircle size={16} className="text-aw-error" />,
  }

  const statusColors: Record<string, string> = {
    pending: 'text-aw-muted',
    running: 'text-aw-accent',
    completed: 'text-aw-success',
    failed: 'text-aw-error',
  }

  return (
    <div
      className={`bg-aw-surface rounded-xl border border-aw-border border-l-4 ${
        priorityColors[task.priority] || 'border-l-aw-muted'
      } overflow-hidden`}
    >
      <div
        className="p-4 cursor-pointer hover:bg-aw-card/30 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-start gap-4">
          <div className="mt-1">{statusIcons[task.status]}</div>
          <div className="flex-1 min-w-0">
            <p className={`${task.status === 'completed' ? 'text-aw-muted' : 'text-aw-text'}`}>
              {task.description}
            </p>
            <div className="flex items-center gap-4 mt-2 text-sm">
              <span className="text-aw-muted">{task.task_type}</span>
              <span className={statusColors[task.status]}>{task.status}</span>
              {task.routed_to && (
                <span className="text-aw-accent">→ {task.routed_to}</span>
              )}
            </div>
          </div>
          {task.result && (
            <ChevronDown
              size={20}
              className={`text-aw-muted transition-transform ${expanded ? 'rotate-180' : ''}`}
            />
          )}
        </div>
      </div>

      {/* Expanded result */}
      {expanded && task.result && (
        <div className="px-4 pb-4 border-t border-aw-border">
          <div className="bg-aw-card rounded-lg p-4 mt-4">
            <h4 className="text-sm font-medium text-aw-muted mb-2">Result</h4>
            <p className="text-sm text-aw-text whitespace-pre-wrap">
              {typeof task.result === 'object' && task.result?.content
                ? task.result.content
                : String(task.result)}
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
