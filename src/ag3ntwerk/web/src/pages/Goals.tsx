import { useEffect, useState } from 'react'
import { useStore } from '../store'
import { Plus, Target, ChevronRight, Check } from 'lucide-react'

export default function Goals() {
  const { goals, fetchGoals, createGoal, updateMilestone } = useStore()
  const [showCreate, setShowCreate] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const [newDescription, setNewDescription] = useState('')
  const [expandedGoal, setExpandedGoal] = useState<string | null>(null)

  useEffect(() => {
    fetchGoals()
  }, [fetchGoals])

  const handleCreate = async () => {
    if (!newTitle.trim()) return
    await createGoal({
      title: newTitle,
      description: newDescription,
    })
    setNewTitle('')
    setNewDescription('')
    setShowCreate(false)
  }

  const activeGoals = goals.filter((g) => g.status !== 'completed' && g.status !== 'abandoned')
  const completedGoals = goals.filter((g) => g.status === 'completed')

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-aw-text">Goals</h1>
          <p className="text-aw-muted mt-1">
            {activeGoals.length} active, {completedGoals.length} achieved
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="flex items-center gap-2 px-4 py-2 bg-aw-accent text-white rounded-lg hover:bg-indigo-600 transition-colors"
        >
          <Plus size={20} />
          New Goal
        </button>
      </div>

      {/* Create Goal Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-aw-surface rounded-xl border border-aw-border p-6 w-full max-w-md">
            <h2 className="text-xl font-semibold text-aw-text mb-4">Create Goal</h2>
            <input
              type="text"
              placeholder="Goal title"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="w-full bg-aw-card border border-aw-border rounded-lg px-4 py-2 text-aw-text mb-3"
              autoFocus
            />
            <textarea
              placeholder="Description (optional)"
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              className="w-full bg-aw-card border border-aw-border rounded-lg px-4 py-2 text-aw-text mb-4 h-24"
            />
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setShowCreate(false)}
                className="px-4 py-2 text-aw-muted hover:text-aw-text"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                className="px-4 py-2 bg-aw-accent text-white rounded-lg hover:bg-indigo-600"
              >
                Create
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Active Goals */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-aw-text mb-4">Active Goals</h2>
        <div className="space-y-4">
          {activeGoals.length > 0 ? (
            activeGoals.map((goal) => (
              <GoalCard
                key={goal.id}
                goal={goal}
                expanded={expandedGoal === goal.id}
                onToggle={() => setExpandedGoal(expandedGoal === goal.id ? null : goal.id)}
                onMilestoneToggle={(milestoneId, currentStatus) => {
                  const newStatus = currentStatus === 'completed' ? 'pending' : 'completed'
                  updateMilestone(goal.id, milestoneId, newStatus)
                }}
              />
            ))
          ) : (
            <div className="bg-aw-surface rounded-xl border border-aw-border p-8 text-center">
              <Target size={48} className="mx-auto mb-2 text-aw-muted opacity-50" />
              <p className="text-aw-muted">No active goals</p>
              <button
                onClick={() => setShowCreate(true)}
                className="mt-2 text-aw-accent hover:underline"
              >
                Set your first goal
              </button>
            </div>
          )}
        </div>
      </section>

      {/* Completed Goals */}
      {completedGoals.length > 0 && (
        <section>
          <h2 className="text-lg font-semibold text-aw-text mb-4">Achieved Goals</h2>
          <div className="space-y-4 opacity-75">
            {completedGoals.slice(0, 5).map((goal) => (
              <GoalCard key={goal.id} goal={goal} completed />
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function GoalCard({
  goal,
  expanded,
  onToggle,
  completed,
  onMilestoneToggle,
}: {
  goal: {
    id: string
    title: string
    description?: string
    status: string
    progress: number
    milestones: { id: string; title: string; status: string }[]
  }
  expanded?: boolean
  onToggle?: () => void
  completed?: boolean
  onMilestoneToggle?: (milestoneId: string, currentStatus: string) => void
}) {
  const completedMilestones = goal.milestones?.filter((m) => m.status === 'completed').length || 0
  const totalMilestones = goal.milestones?.length || 0
  const progress = totalMilestones > 0 ? (completedMilestones / totalMilestones) * 100 : goal.progress

  return (
    <div className="bg-aw-surface rounded-xl border border-aw-border overflow-hidden">
      <div
        className="p-4 flex items-center gap-4 cursor-pointer hover:bg-aw-card/50 transition-colors"
        onClick={onToggle}
      >
        <div
          className={`p-3 rounded-lg ${
            completed ? 'bg-aw-success/20' : 'bg-aw-accent/20'
          }`}
        >
          {completed ? (
            <Check size={24} className="text-aw-success" />
          ) : (
            <Target size={24} className="text-aw-accent" />
          )}
        </div>

        <div className="flex-1 min-w-0">
          <h3
            className={`font-semibold ${
              completed ? 'text-aw-muted line-through' : 'text-aw-text'
            }`}
          >
            {goal.title}
          </h3>
          {goal.description && (
            <p className="text-sm text-aw-muted truncate">{goal.description}</p>
          )}

          {/* Progress bar */}
          <div className="mt-2 flex items-center gap-3">
            <div className="flex-1 h-2 bg-aw-card rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  completed ? 'bg-aw-success' : 'bg-aw-accent'
                }`}
                style={{ width: `${progress}%` }}
              />
            </div>
            <span className="text-sm text-aw-muted">
              {totalMilestones > 0
                ? `${completedMilestones}/${totalMilestones}`
                : `${progress.toFixed(0)}%`}
            </span>
          </div>
        </div>

        {onToggle && (
          <ChevronRight
            size={20}
            className={`text-aw-muted transition-transform ${
              expanded ? 'rotate-90' : ''
            }`}
          />
        )}
      </div>

      {/* Expanded milestones */}
      {expanded && goal.milestones && goal.milestones.length > 0 && (
        <div className="border-t border-aw-border p-4 bg-aw-card/30">
          <h4 className="text-sm font-medium text-aw-muted mb-3">Milestones</h4>
          <div className="space-y-2">
            {goal.milestones.map((milestone) => (
              <div
                key={milestone.id}
                className="flex items-center gap-3 cursor-pointer hover:bg-aw-card/50 rounded p-1 -m-1 transition-colors"
                onClick={(e) => {
                  e.stopPropagation()
                  onMilestoneToggle?.(milestone.id, milestone.status)
                }}
              >
                <div
                  className={`w-5 h-5 rounded-full border-2 flex items-center justify-center ${
                    milestone.status === 'completed'
                      ? 'bg-aw-success border-aw-success'
                      : 'border-aw-border hover:border-aw-muted'
                  }`}
                >
                  {milestone.status === 'completed' && (
                    <Check size={12} className="text-white" />
                  )}
                </div>
                <span
                  className={`text-sm ${
                    milestone.status === 'completed'
                      ? 'text-aw-muted line-through'
                      : 'text-aw-text'
                  }`}
                >
                  {milestone.title}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
