import { useEffect, useState } from 'react'
import {
  FileText,
  Share2,
  Zap,
  Plus,
  RefreshCw,
  ChevronRight,
  CheckCircle,
  Clock,
  BarChart3,
  Play,
  Square,
} from 'lucide-react'

interface ContentPiece {
  id: string
  title: string
  body: string
  format: string
  summary: string
  tags: string[]
  published_platforms: string[]
  created_at: string
}

interface PipelineExecution {
  id: string
  campaign: string
  audience: string
  channels: string[]
  status: string
  current_step: string | null
  steps: { name: string; status: string; executive: string }[]
  started_at: string
  completed_at: string | null
  content_created: number
  content_distributed: number
}

interface ContentStats {
  content: {
    total_pieces: number
    by_format: Record<string, number>
  }
  distribution: {
    total_distributions: number
    platforms_used: string[]
    recent_count: number
  }
  pipeline: {
    total_executions: number
    active: number
    completed: number
  }
}

const API_BASE = '/api/v1/content'

export default function ContentPipeline() {
  const [content, setContent] = useState<ContentPiece[]>([])
  const [executions, setExecutions] = useState<PipelineExecution[]>([])
  const [stats, setStats] = useState<ContentStats | null>(null)
  const [showCreateContent, setShowCreateContent] = useState(false)
  const [showStartPipeline, setShowStartPipeline] = useState(false)
  const [selectedExecution, setSelectedExecution] = useState<PipelineExecution | null>(null)

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [])

  const fetchAll = () => {
    fetchContent()
    fetchExecutions()
    fetchStats()
  }

  const fetchContent = async () => {
    try {
      const res = await fetch(`${API_BASE}/pieces`)
      if (res.ok) {
        const data = await res.json()
        setContent(data.content || [])
      }
    } catch (e) {
      console.error('Failed to fetch content:', e)
    }
  }

  const fetchExecutions = async () => {
    try {
      const res = await fetch(`${API_BASE}/pipeline/executions`)
      if (res.ok) {
        const data = await res.json()
        setExecutions(data.executions || [])
      }
    } catch (e) {
      console.error('Failed to fetch executions:', e)
    }
  }

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`)
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (e) {
      console.error('Failed to fetch stats:', e)
    }
  }

  const advancePipeline = async (executionId: string) => {
    try {
      const res = await fetch(`${API_BASE}/pipeline/executions/${executionId}/advance`, {
        method: 'POST',
      })
      if (res.ok) {
        fetchExecutions()
      }
    } catch (e) {
      console.error('Failed to advance pipeline:', e)
    }
  }

  const cancelPipeline = async (executionId: string) => {
    try {
      const res = await fetch(`${API_BASE}/pipeline/executions/${executionId}/cancel`, {
        method: 'POST',
      })
      if (res.ok) {
        fetchExecutions()
        setSelectedExecution(null)
      }
    } catch (e) {
      console.error('Failed to cancel pipeline:', e)
    }
  }

  // Track active executions for potential future use
  void executions.filter((e) => e.status === 'in_progress')

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-csuite-text">Content Pipeline</h1>
          <p className="text-csuite-muted mt-1">
            Monitor content creation and distribution workflows
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowStartPipeline(true)}
            className="flex items-center gap-2 px-4 py-2 bg-csuite-success text-white rounded-lg hover:bg-green-600"
          >
            <Play size={18} />
            Start Pipeline
          </button>
          <button
            onClick={() => setShowCreateContent(true)}
            className="flex items-center gap-2 px-4 py-2 bg-csuite-accent text-white rounded-lg hover:bg-indigo-600"
          >
            <Plus size={18} />
            New Content
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <StatCard
            icon={FileText}
            label="Content Pieces"
            value={stats.content.total_pieces}
            color="accent"
          />
          <StatCard
            icon={Share2}
            label="Distributions"
            value={stats.distribution.total_distributions}
            color="success"
          />
          <StatCard
            icon={Zap}
            label="Active Pipelines"
            value={stats.pipeline.active}
            color="warning"
          />
          <StatCard
            icon={BarChart3}
            label="Completed Pipelines"
            value={stats.pipeline.completed}
            color="success"
          />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Active Pipelines */}
        <div className="lg:col-span-2 space-y-6">
          {/* Pipeline Executions */}
          <section className="bg-csuite-surface rounded-xl border border-csuite-border p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-csuite-text flex items-center gap-2">
                <Zap size={20} className="text-csuite-warning" />
                Pipeline Executions
              </h2>
              <button
                onClick={fetchExecutions}
                className="text-csuite-muted hover:text-csuite-text"
              >
                <RefreshCw size={18} />
              </button>
            </div>

            {executions.length > 0 ? (
              <div className="space-y-3">
                {executions.slice(0, 5).map((execution) => (
                  <div
                    key={execution.id}
                    className="bg-csuite-card rounded-lg p-4 cursor-pointer hover:bg-csuite-surface transition-colors"
                    onClick={() => setSelectedExecution(execution)}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h3 className="font-medium text-csuite-text">{execution.campaign}</h3>
                      <StatusBadge status={execution.status} />
                    </div>
                    {execution.current_step && (
                      <p className="text-sm text-csuite-muted mb-2">
                        Current: {formatStepName(execution.current_step)}
                      </p>
                    )}
                    <div className="flex items-center gap-4 text-xs text-csuite-muted">
                      <span>
                        {execution.steps.filter((s) => s.status === 'completed').length}/
                        {execution.steps.length} steps
                      </span>
                      {execution.channels.length > 0 && (
                        <span>{execution.channels.join(', ')}</span>
                      )}
                    </div>
                    {execution.status === 'in_progress' && (
                      <div className="mt-3 h-1.5 bg-csuite-surface rounded-full overflow-hidden">
                        <div
                          className="h-full bg-csuite-accent rounded-full transition-all"
                          style={{
                            width: `${
                              (execution.steps.filter((s) => s.status === 'completed').length /
                                execution.steps.length) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Zap size={48} className="mx-auto mb-2 text-csuite-muted opacity-50" />
                <p className="text-csuite-muted">No pipeline executions yet</p>
                <p className="text-sm text-csuite-muted mt-1">Start a pipeline to see it here</p>
              </div>
            )}
          </section>

          {/* Content Library */}
          <section className="bg-csuite-surface rounded-xl border border-csuite-border p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-csuite-text flex items-center gap-2">
                <FileText size={20} className="text-csuite-accent" />
                Content Library
              </h2>
              <button
                onClick={fetchContent}
                className="text-csuite-muted hover:text-csuite-text"
              >
                <RefreshCw size={18} />
              </button>
            </div>

            {content.length > 0 ? (
              <div className="space-y-3">
                {content.slice(0, 5).map((piece) => (
                  <div key={piece.id} className="bg-csuite-card rounded-lg p-4">
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-csuite-text">{piece.title}</h3>
                        <p className="text-sm text-csuite-muted mt-1 line-clamp-2">
                          {piece.summary || piece.body.slice(0, 100) + '...'}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs px-2 py-0.5 bg-csuite-surface rounded text-csuite-muted">
                            {piece.format}
                          </span>
                          {piece.published_platforms.length > 0 && (
                            <span className="text-xs text-csuite-success flex items-center gap-1">
                              <Share2 size={12} />
                              {piece.published_platforms.length} platforms
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <FileText size={48} className="mx-auto mb-2 text-csuite-muted opacity-50" />
                <p className="text-csuite-muted">No content yet</p>
              </div>
            )}
          </section>
        </div>

        {/* Right Sidebar */}
        <div className="space-y-6">
          {/* Format Breakdown */}
          {stats && Object.keys(stats.content.by_format).length > 0 && (
            <section className="bg-csuite-surface rounded-xl border border-csuite-border p-6">
              <h2 className="text-lg font-semibold text-csuite-text mb-4">Content by Format</h2>
              <div className="space-y-3">
                {Object.entries(stats.content.by_format).map(([format, count]) => (
                  <div key={format} className="flex items-center justify-between">
                    <span className="text-csuite-text capitalize">{format.replace('_', ' ')}</span>
                    <span className="text-csuite-muted">{count}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Platforms */}
          {stats && stats.distribution.platforms_used.length > 0 && (
            <section className="bg-csuite-surface rounded-xl border border-csuite-border p-6">
              <h2 className="text-lg font-semibold text-csuite-text mb-4">Active Platforms</h2>
              <div className="flex flex-wrap gap-2">
                {stats.distribution.platforms_used.map((platform) => (
                  <span
                    key={platform}
                    className="px-3 py-1 bg-csuite-card rounded-full text-sm text-csuite-text"
                  >
                    {platform}
                  </span>
                ))}
              </div>
            </section>
          )}

          {/* Quick Actions */}
          <section className="bg-csuite-surface rounded-xl border border-csuite-border p-6">
            <h2 className="text-lg font-semibold text-csuite-text mb-4">Quick Actions</h2>
            <div className="space-y-2">
              <button
                onClick={() => setShowStartPipeline(true)}
                className="w-full flex items-center gap-3 p-3 bg-csuite-card rounded-lg hover:bg-csuite-accent/10 transition-colors"
              >
                <Play size={18} className="text-csuite-success" />
                <span className="text-csuite-text">Start New Pipeline</span>
              </button>
              <button
                onClick={() => setShowCreateContent(true)}
                className="w-full flex items-center gap-3 p-3 bg-csuite-card rounded-lg hover:bg-csuite-accent/10 transition-colors"
              >
                <Plus size={18} className="text-csuite-accent" />
                <span className="text-csuite-text">Create Content</span>
              </button>
              <button
                onClick={fetchAll}
                className="w-full flex items-center gap-3 p-3 bg-csuite-card rounded-lg hover:bg-csuite-accent/10 transition-colors"
              >
                <RefreshCw size={18} className="text-csuite-muted" />
                <span className="text-csuite-text">Refresh All</span>
              </button>
            </div>
          </section>
        </div>
      </div>

      {/* Pipeline Detail Modal */}
      {selectedExecution && (
        <PipelineDetailModal
          execution={selectedExecution}
          onClose={() => setSelectedExecution(null)}
          onAdvance={() => advancePipeline(selectedExecution.id)}
          onCancel={() => cancelPipeline(selectedExecution.id)}
        />
      )}

      {/* Create Content Modal */}
      {showCreateContent && (
        <CreateContentModal
          onClose={() => setShowCreateContent(false)}
          onCreated={() => {
            setShowCreateContent(false)
            fetchContent()
            fetchStats()
          }}
        />
      )}

      {/* Start Pipeline Modal */}
      {showStartPipeline && (
        <StartPipelineModal
          onClose={() => setShowStartPipeline(false)}
          onStarted={() => {
            setShowStartPipeline(false)
            fetchExecutions()
            fetchStats()
          }}
        />
      )}
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
  value: number
  color: 'success' | 'warning' | 'error' | 'accent'
}) {
  const colorMap = {
    success: 'text-csuite-success',
    warning: 'text-csuite-warning',
    error: 'text-csuite-error',
    accent: 'text-csuite-accent',
  }

  return (
    <div className="bg-csuite-surface rounded-xl border border-csuite-border p-4">
      <div className="flex items-center gap-2 text-csuite-muted mb-2">
        <Icon size={16} />
        <span className="text-sm">{label}</span>
      </div>
      <p className={`text-2xl font-bold ${colorMap[color]}`}>{value}</p>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    in_progress: 'bg-csuite-warning/20 text-csuite-warning',
    completed: 'bg-csuite-success/20 text-csuite-success',
    cancelled: 'bg-csuite-error/20 text-csuite-error',
    pending: 'bg-csuite-muted/20 text-csuite-muted',
  }

  return (
    <span className={`text-xs px-2 py-0.5 rounded ${styles[status] || styles.pending}`}>
      {status.replace('_', ' ')}
    </span>
  )
}

function formatStepName(step: string): string {
  return step.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())
}

function PipelineDetailModal({
  execution,
  onClose,
  onAdvance,
  onCancel,
}: {
  execution: PipelineExecution
  onClose: () => void
  onAdvance: () => void
  onCancel: () => void
}) {
  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-csuite-surface rounded-xl border border-csuite-border p-6 w-full max-w-lg">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-csuite-text">{execution.campaign}</h2>
          <StatusBadge status={execution.status} />
        </div>

        <div className="space-y-4 mb-6">
          {execution.steps.map((step, index) => (
            <div key={step.name} className="flex items-center gap-3">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  step.status === 'completed'
                    ? 'bg-csuite-success/20'
                    : step.status === 'in_progress'
                    ? 'bg-csuite-warning/20'
                    : 'bg-csuite-card'
                }`}
              >
                {step.status === 'completed' ? (
                  <CheckCircle size={16} className="text-csuite-success" />
                ) : step.status === 'in_progress' ? (
                  <Clock size={16} className="text-csuite-warning animate-pulse" />
                ) : (
                  <span className="text-xs text-csuite-muted">{index + 1}</span>
                )}
              </div>
              <div className="flex-1">
                <p className="text-csuite-text">{formatStepName(step.name)}</p>
                <p className="text-xs text-csuite-muted">{step.executive}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-csuite-card border border-csuite-border text-csuite-text rounded-lg hover:bg-csuite-surface"
          >
            Close
          </button>
          <div className="flex gap-2">
            {execution.status === 'in_progress' && (
              <>
                <button
                  onClick={onCancel}
                  className="flex items-center gap-2 px-4 py-2 text-csuite-error hover:bg-csuite-error/10 rounded-lg"
                >
                  <Square size={16} />
                  Cancel
                </button>
                <button
                  onClick={onAdvance}
                  className="flex items-center gap-2 px-4 py-2 bg-csuite-accent text-white rounded-lg hover:bg-indigo-600"
                >
                  <ChevronRight size={16} />
                  Advance Step
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function CreateContentModal({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: () => void
}) {
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [format, setFormat] = useState('article')
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async () => {
    if (!title.trim() || !body.trim()) return

    setIsSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/pieces`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: title.trim(),
          body: body.trim(),
          format,
        }),
      })
      if (res.ok) {
        onCreated()
      }
    } catch (e) {
      console.error('Failed to create content:', e)
    }
    setIsSubmitting(false)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-csuite-surface rounded-xl border border-csuite-border p-6 w-full max-w-lg">
        <h2 className="text-xl font-semibold text-csuite-text mb-4">Create Content</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-csuite-muted mb-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Content title"
              className="w-full p-3 bg-csuite-card border border-csuite-border rounded-lg text-csuite-text placeholder-csuite-muted focus:outline-none focus:border-csuite-accent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-csuite-muted mb-1">Format</label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="w-full p-3 bg-csuite-card border border-csuite-border rounded-lg text-csuite-text focus:outline-none focus:border-csuite-accent"
            >
              <option value="article">Article</option>
              <option value="blog_post">Blog Post</option>
              <option value="social_post">Social Post</option>
              <option value="newsletter">Newsletter</option>
              <option value="video_script">Video Script</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-csuite-muted mb-1">Content</label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Write your content here..."
              rows={6}
              className="w-full p-3 bg-csuite-card border border-csuite-border rounded-lg text-csuite-text placeholder-csuite-muted resize-none focus:outline-none focus:border-csuite-accent"
            />
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-csuite-card border border-csuite-border text-csuite-text rounded-lg hover:bg-csuite-surface"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!title.trim() || !body.trim() || isSubmitting}
            className="px-4 py-2 bg-csuite-accent text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50"
          >
            {isSubmitting ? 'Creating...' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  )
}

function StartPipelineModal({
  onClose,
  onStarted,
}: {
  onClose: () => void
  onStarted: () => void
}) {
  const [campaign, setCampaign] = useState('')
  const [audience, setAudience] = useState('')
  const [channels, setChannels] = useState<string[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)

  const channelOptions = ['twitter', 'linkedin', 'blog', 'newsletter', 'youtube']

  const toggleChannel = (channel: string) => {
    if (channels.includes(channel)) {
      setChannels(channels.filter((c) => c !== channel))
    } else {
      setChannels([...channels, channel])
    }
  }

  const handleSubmit = async () => {
    if (!campaign.trim()) return

    setIsSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/pipeline/start`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          campaign: campaign.trim(),
          audience: audience.trim(),
          channels,
          content_types: [],
        }),
      })
      if (res.ok) {
        onStarted()
      }
    } catch (e) {
      console.error('Failed to start pipeline:', e)
    }
    setIsSubmitting(false)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-csuite-surface rounded-xl border border-csuite-border p-6 w-full max-w-lg">
        <h2 className="text-xl font-semibold text-csuite-text mb-4">Start Content Pipeline</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-csuite-muted mb-1">
              Campaign Name
            </label>
            <input
              type="text"
              value={campaign}
              onChange={(e) => setCampaign(e.target.value)}
              placeholder="e.g., Q1 Product Launch"
              className="w-full p-3 bg-csuite-card border border-csuite-border rounded-lg text-csuite-text placeholder-csuite-muted focus:outline-none focus:border-csuite-accent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-csuite-muted mb-1">
              Target Audience
            </label>
            <input
              type="text"
              value={audience}
              onChange={(e) => setAudience(e.target.value)}
              placeholder="e.g., Tech founders and developers"
              className="w-full p-3 bg-csuite-card border border-csuite-border rounded-lg text-csuite-text placeholder-csuite-muted focus:outline-none focus:border-csuite-accent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-csuite-muted mb-2">
              Distribution Channels
            </label>
            <div className="flex flex-wrap gap-2">
              {channelOptions.map((channel) => (
                <button
                  key={channel}
                  onClick={() => toggleChannel(channel)}
                  className={`px-3 py-1.5 rounded-lg text-sm transition-colors ${
                    channels.includes(channel)
                      ? 'bg-csuite-accent text-white'
                      : 'bg-csuite-card text-csuite-muted hover:text-csuite-text'
                  }`}
                >
                  {channel}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-csuite-card border border-csuite-border text-csuite-text rounded-lg hover:bg-csuite-surface"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!campaign.trim() || isSubmitting}
            className="flex items-center gap-2 px-4 py-2 bg-csuite-success text-white rounded-lg hover:bg-green-600 disabled:opacity-50"
          >
            <Play size={16} />
            {isSubmitting ? 'Starting...' : 'Start Pipeline'}
          </button>
        </div>
      </div>
    </div>
  )
}
