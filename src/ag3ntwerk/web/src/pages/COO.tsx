import { useEffect, useState } from 'react'
import { useStore } from '../store'
import {
  Brain,
  Play,
  Square,
  Activity,
  Clock,
  CheckCircle,
  DollarSign,
  Gauge,
  Eye,
  Shield,
  Zap,
  Pause,
} from 'lucide-react'

export default function COO() {
  const { cooStatus, fetchCOOStatus, startCOO, stopCOO, setCOOMode, approveSuggestion, rejectSuggestion } = useStore()
  const [suggestions, setSuggestions] = useState<any>(null)
  const [loadingSuggestions, setLoadingSuggestions] = useState(false)

  useEffect(() => {
    fetchCOOStatus()
    const interval = setInterval(fetchCOOStatus, 5000)
    return () => clearInterval(interval)
  }, [fetchCOOStatus])

  const fetchSuggestions = async () => {
    setLoadingSuggestions(true)
    try {
      const res = await fetch('/api/v1/coo/suggestions')
      if (res.ok) {
        setSuggestions(await res.json())
      }
    } catch (e) {
      console.error('Failed to fetch suggestions:', e)
    }
    setLoadingSuggestions(false)
  }

  const executeSuggestion = async () => {
    if (!suggestions?.suggestion?.id) return
    const success = await approveSuggestion(suggestions.suggestion.id)
    if (success) {
      setSuggestions(null)
      fetchSuggestions()
    }
  }

  const skipSuggestion = async () => {
    if (!suggestions?.suggestion?.id) return
    const success = await rejectSuggestion(suggestions.suggestion.id)
    if (success) {
      setSuggestions(null)
      fetchSuggestions()
    }
  }

  const isRunning =
    cooStatus?.state &&
    cooStatus.state !== 'idle' &&
    cooStatus.state !== 'not_available' &&
    cooStatus.state !== 'unknown'

  const modes = [
    { value: 'autonomous', label: 'Autonomous', icon: Zap, description: 'Full autonomous operation' },
    { value: 'supervised', label: 'Supervised', icon: Eye, description: 'Execute but report all actions' },
    { value: 'approval', label: 'Approval', icon: Shield, description: 'Request approval for each action' },
    { value: 'observe', label: 'Observe', icon: Eye, description: 'Only observe and recommend' },
    { value: 'paused', label: 'Paused', icon: Pause, description: 'Temporarily halted' },
  ]

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
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
            <h1 className="text-3xl font-bold text-aw-text">Autonomous COO</h1>
            <p className="text-aw-muted mt-1">
              {isRunning ? 'Running' : 'Idle'} • Mode: {cooStatus?.mode || 'unknown'}
            </p>
          </div>
        </div>

        <button
          onClick={isRunning ? stopCOO : startCOO}
          className={`flex items-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors ${
            isRunning
              ? 'bg-aw-error hover:bg-red-600 text-white'
              : 'bg-aw-success hover:bg-green-600 text-white'
          }`}
        >
          {isRunning ? (
            <>
              <Square size={20} />
              Stop COO
            </>
          ) : (
            <>
              <Play size={20} />
              Start COO
            </>
          )}
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={Activity}
          label="State"
          value={cooStatus?.state || 'unknown'}
          isState
        />
        <StatCard
          icon={Clock}
          label="Uptime"
          value={formatUptime(cooStatus?.uptime_seconds || 0)}
        />
        <StatCard
          icon={CheckCircle}
          label="Successful"
          value={String(cooStatus?.successful_executions || 0)}
          color="success"
        />
        <StatCard
          icon={DollarSign}
          label="Daily Spend"
          value={`$${(cooStatus?.daily_spend_usd || 0).toFixed(2)}`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Mode Selection */}
        <div className="bg-aw-surface rounded-xl border border-aw-border p-6">
          <h2 className="text-xl font-semibold text-aw-text mb-4">Operating Mode</h2>
          <div className="space-y-3">
            {modes.map(({ value, label, icon: Icon, description }) => (
              <button
                key={value}
                onClick={() => setCOOMode(value)}
                className={`w-full flex items-center gap-4 p-4 rounded-lg border transition-colors ${
                  cooStatus?.mode === value
                    ? 'border-aw-accent bg-aw-accent/10'
                    : 'border-aw-border hover:border-aw-muted'
                }`}
              >
                <Icon
                  size={24}
                  className={
                    cooStatus?.mode === value
                      ? 'text-aw-accent'
                      : 'text-aw-muted'
                  }
                />
                <div className="text-left">
                  <p
                    className={`font-medium ${
                      cooStatus?.mode === value
                        ? 'text-aw-accent'
                        : 'text-aw-text'
                    }`}
                  >
                    {label}
                  </p>
                  <p className="text-sm text-aw-muted">{description}</p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Suggestions */}
        <div className="bg-aw-surface rounded-xl border border-aw-border p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-aw-text">Next Suggestion</h2>
            <button
              onClick={fetchSuggestions}
              disabled={loadingSuggestions}
              className="text-sm text-aw-accent hover:underline disabled:opacity-50"
            >
              {loadingSuggestions ? 'Loading...' : 'Refresh'}
            </button>
          </div>

          {suggestions?.suggestion ? (
            <div className="bg-aw-card rounded-lg p-4">
              <h3 className="font-medium text-aw-text mb-2">
                {suggestions.suggestion.item?.title || 'Unnamed task'}
              </h3>
              <div className="grid grid-cols-2 gap-4 text-sm mb-4">
                <div>
                  <span className="text-aw-muted">Executor:</span>
                  <span className="ml-2 text-aw-text">
                    {suggestions.decision?.executor || 'unknown'}
                  </span>
                </div>
                <div>
                  <span className="text-aw-muted">Confidence:</span>
                  <span className="ml-2 text-aw-text">
                    {((suggestions.decision?.confidence || 0) * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
              <p className="text-sm text-aw-muted mb-4">
                {suggestions.decision?.reason}
              </p>
              <div className="flex gap-3">
                <button
                  onClick={executeSuggestion}
                  className="flex-1 px-4 py-2 bg-aw-accent text-white rounded-lg hover:bg-indigo-600"
                >
                  Execute Now
                </button>
                <button
                  onClick={skipSuggestion}
                  className="px-4 py-2 bg-aw-card border border-aw-border text-aw-text rounded-lg hover:bg-aw-surface"
                >
                  Skip
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center py-8">
              <Gauge size={48} className="mx-auto mb-2 text-aw-muted opacity-50" />
              <p className="text-aw-muted">
                {suggestions?.reason || 'Click refresh to get suggestions'}
              </p>
            </div>
          )}

          {/* Context summary */}
          {suggestions?.context_summary && (
            <div className="mt-4 pt-4 border-t border-aw-border">
              <h4 className="text-sm font-medium text-aw-muted mb-2">Context</h4>
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-aw-muted">Goals:</span>
                  <span className="ml-2 text-aw-text">
                    {suggestions.context_summary.active_goals}
                  </span>
                </div>
                <div>
                  <span className="text-aw-muted">Tasks:</span>
                  <span className="ml-2 text-aw-text">
                    {suggestions.context_summary.pending_tasks}
                  </span>
                </div>
                <div>
                  <span className="text-aw-muted">Blockers:</span>
                  <span className="ml-2 text-aw-text">
                    {suggestions.context_summary.blockers}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Pending Approvals */}
      {cooStatus && (cooStatus.pending_approvals || 0) > 0 && (
        <div className="mt-6 bg-aw-surface rounded-xl border border-aw-border p-6">
          <h2 className="text-xl font-semibold text-aw-text mb-4">
            Pending Approvals ({cooStatus.pending_approvals})
          </h2>
          <p className="text-aw-muted">
            Approval requests will appear here when the COO needs your decision.
          </p>
        </div>
      )}
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
  color,
  isState,
}: {
  icon: React.ElementType
  label: string
  value: string
  color?: 'success' | 'warning' | 'error'
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
    not_available: 'text-aw-error',
    unknown: 'text-aw-muted',
  }

  const colorMap = {
    success: 'text-aw-success',
    warning: 'text-aw-warning',
    error: 'text-aw-error',
  }

  const valueColor = isState
    ? stateColors[value] || 'text-aw-text'
    : color
    ? colorMap[color]
    : 'text-aw-text'

  return (
    <div className="bg-aw-surface rounded-xl border border-aw-border p-4">
      <div className="flex items-center gap-2 text-aw-muted mb-2">
        <Icon size={16} />
        <span className="text-sm">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${valueColor}`}>{value}</p>
    </div>
  )
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}
