import { useEffect, useState } from 'react'
import { useStore } from '../store'
import {
  Headphones,
  ListChecks,
  Tag,
  ChevronDown,
  ChevronRight,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader,
  FileText,
  RefreshCw,
  Upload,
  Trash2,
} from 'lucide-react'

const API_BASE = '/api/v1/meetings'

interface MeetingDetail {
  id: string
  title: string
  audio_file: string
  status: string
  duration_seconds: number | null
  transcript_text: string | null
  analysis: {
    executive_summary: string
    key_decisions: { summary: string; context: string; decided_by: string | null }[]
    action_items: { description: string; assignee: string | null; deadline: string | null; priority: string }[]
    themes: string[]
    questions: { question: string; answered: boolean; answer: string | null }[]
    sentiment: string
    participants: { name: string; role: string | null }[]
  } | null
  tags: string[]
  error: string | null
  created_at: string
}

interface ThemeTrend {
  theme: string
  count: number
}

type TabId = 'meetings' | 'action-items' | 'themes'

const statusIcon = (status: string) => {
  switch (status) {
    case 'complete': return <CheckCircle size={16} className="text-ag3ntwerk-success" />
    case 'failed': return <AlertCircle size={16} className="text-red-400" />
    case 'transcribing':
    case 'analyzing':
      return <Loader size={16} className="text-ag3ntwerk-accent animate-spin" />
    default: return <Clock size={16} className="text-ag3ntwerk-muted" />
  }
}

const priorityColor = (p: string) => {
  switch (p) {
    case 'high': return 'text-red-400'
    case 'medium': return 'text-yellow-400'
    default: return 'text-ag3ntwerk-muted'
  }
}

const statusOptions = ['open', 'in_progress', 'done', 'cancelled']

function formatDuration(seconds: number | null): string {
  if (!seconds) return '--'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return m > 0 ? `${m}m ${s}s` : `${s}s`
}

export default function Meetings() {
  const { meetings, actionItems, fetchMeetings, fetchActionItems, updateActionItem } = useStore()
  const [activeTab, setActiveTab] = useState<TabId>('meetings')
  const [expandedMeeting, setExpandedMeeting] = useState<string | null>(null)
  const [meetingDetail, setMeetingDetail] = useState<MeetingDetail | null>(null)
  const [themes, setThemes] = useState<ThemeTrend[]>([])
  const [statusFilter, setStatusFilter] = useState<string>('')
  const [isUploading, setIsUploading] = useState(false)

  useEffect(() => {
    fetchMeetings()
    fetchActionItems()
    fetchThemes()
  }, [fetchMeetings, fetchActionItems])

  const fetchThemes = async () => {
    try {
      const res = await fetch(`${API_BASE}/themes`)
      if (res.ok) {
        const data = await res.json()
        setThemes(data.themes || [])
      }
    } catch (e) {
      console.error('Failed to fetch themes:', e)
    }
  }

  const fetchDetail = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE}/${id}`)
      if (res.ok) {
        const data = await res.json()
        setMeetingDetail(data)
      }
    } catch (e) {
      console.error('Failed to fetch meeting detail:', e)
    }
  }

  const handleExpand = (id: string) => {
    if (expandedMeeting === id) {
      setExpandedMeeting(null)
      setMeetingDetail(null)
    } else {
      setExpandedMeeting(id)
      fetchDetail(id)
    }
  }

  const handleReprocess = async (id: string) => {
    try {
      await fetch(`${API_BASE}/${id}/reprocess`, { method: 'POST' })
      fetchMeetings()
      fetchDetail(id)
    } catch (e) {
      console.error('Failed to reprocess:', e)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      await fetch(`${API_BASE}/${id}`, { method: 'DELETE' })
      setExpandedMeeting(null)
      setMeetingDetail(null)
      fetchMeetings()
      fetchActionItems()
    } catch (e) {
      console.error('Failed to delete:', e)
    }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setIsUploading(true)
    try {
      const form = new FormData()
      form.append('audio', file)
      form.append('source', 'upload')
      await fetch(`${API_BASE}/upload`, { method: 'POST', body: form })
      fetchMeetings()
    } catch (err) {
      console.error('Upload failed:', err)
    }
    setIsUploading(false)
    e.target.value = ''
  }

  const handleStatusChange = async (itemId: string, newStatus: string) => {
    await updateActionItem(itemId, { status: newStatus })
  }

  const tabs: { id: TabId; label: string; icon: typeof Headphones }[] = [
    { id: 'meetings', label: 'Meetings', icon: Headphones },
    { id: 'action-items', label: 'Action Items', icon: ListChecks },
    { id: 'themes', label: 'Themes', icon: Tag },
  ]

  const maxThemeCount = themes.length > 0 ? Math.max(...themes.map(t => t.count)) : 1

  const filteredItems = statusFilter
    ? actionItems.filter(i => i.status === statusFilter)
    : actionItems

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-ag3ntwerk-text">Meeting Intelligence</h1>
          <p className="text-ag3ntwerk-muted text-sm mt-1">
            {meetings.length} meetings &middot; {actionItems.filter(i => i.status === 'open').length} open action items
          </p>
        </div>
        <label className="flex items-center gap-2 px-4 py-2 bg-ag3ntwerk-accent text-white rounded-lg cursor-pointer hover:bg-ag3ntwerk-accent/80 transition-colors">
          <Upload size={16} />
          {isUploading ? 'Uploading...' : 'Upload Recording'}
          <input type="file" accept="audio/*" onChange={handleUpload} className="hidden" disabled={isUploading} />
        </label>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-ag3ntwerk-border">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeTab === id
                ? 'border-ag3ntwerk-accent text-ag3ntwerk-accent'
                : 'border-transparent text-ag3ntwerk-muted hover:text-ag3ntwerk-text'
            }`}
          >
            <Icon size={16} />
            {label}
          </button>
        ))}
      </div>

      {/* Meetings Tab */}
      {activeTab === 'meetings' && (
        <div className="space-y-2">
          {meetings.length === 0 ? (
            <div className="text-center text-ag3ntwerk-muted py-12">
              <Headphones size={48} className="mx-auto mb-4 opacity-30" />
              <p>No meetings yet. Upload a recording or start the audio watcher.</p>
            </div>
          ) : (
            meetings.map(m => (
              <div key={m.id} className="bg-ag3ntwerk-card rounded-lg border border-ag3ntwerk-border">
                <button
                  onClick={() => handleExpand(m.id)}
                  className="w-full flex items-center justify-between p-4 text-left hover:bg-ag3ntwerk-surface/50 transition-colors rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    {statusIcon(m.status)}
                    <div>
                      <span className="text-ag3ntwerk-text font-medium">{m.title || 'Untitled'}</span>
                      <div className="flex items-center gap-3 text-xs text-ag3ntwerk-muted mt-0.5">
                        <span>{new Date(m.created_at).toLocaleDateString()}</span>
                        <span>{formatDuration(m.duration_seconds)}</span>
                        <span>{m.action_item_count} action items</span>
                      </div>
                    </div>
                  </div>
                  {expandedMeeting === m.id ? <ChevronDown size={16} className="text-ag3ntwerk-muted" /> : <ChevronRight size={16} className="text-ag3ntwerk-muted" />}
                </button>

                {expandedMeeting === m.id && meetingDetail && (
                  <div className="border-t border-ag3ntwerk-border p-4 space-y-4">
                    {/* Actions */}
                    <div className="flex gap-2">
                      <button onClick={() => handleReprocess(m.id)} className="flex items-center gap-1 text-xs text-ag3ntwerk-muted hover:text-ag3ntwerk-accent">
                        <RefreshCw size={14} /> Reprocess
                      </button>
                      <button onClick={() => handleDelete(m.id)} className="flex items-center gap-1 text-xs text-ag3ntwerk-muted hover:text-red-400">
                        <Trash2 size={14} /> Delete
                      </button>
                    </div>

                    {meetingDetail.error && (
                      <div className="bg-red-900/20 border border-red-800 rounded p-3 text-red-300 text-sm">
                        {meetingDetail.error}
                      </div>
                    )}

                    {meetingDetail.analysis && (
                      <>
                        {/* Summary */}
                        <div>
                          <h3 className="text-sm font-semibold text-ag3ntwerk-text mb-1">Summary</h3>
                          <p className="text-sm text-ag3ntwerk-muted whitespace-pre-wrap">{meetingDetail.analysis.executive_summary}</p>
                        </div>

                        {/* Sentiment + Participants */}
                        <div className="flex gap-4 flex-wrap">
                          <span className="text-xs bg-ag3ntwerk-surface px-2 py-1 rounded text-ag3ntwerk-muted">
                            Sentiment: {meetingDetail.analysis.sentiment}
                          </span>
                          {meetingDetail.analysis.participants.map((p, i) => (
                            <span key={i} className="text-xs bg-ag3ntwerk-surface px-2 py-1 rounded text-ag3ntwerk-muted">
                              {p.name}{p.role ? ` (${p.role})` : ''}
                            </span>
                          ))}
                        </div>

                        {/* Decisions */}
                        {meetingDetail.analysis.key_decisions.length > 0 && (
                          <div>
                            <h3 className="text-sm font-semibold text-ag3ntwerk-text mb-1">Key Decisions</h3>
                            <ul className="space-y-1">
                              {meetingDetail.analysis.key_decisions.map((d, i) => (
                                <li key={i} className="text-sm text-ag3ntwerk-muted">
                                  <span className="text-ag3ntwerk-text">{d.summary}</span>
                                  {d.context && <span className="text-xs ml-2">({d.context})</span>}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Themes */}
                        {meetingDetail.analysis.themes.length > 0 && (
                          <div className="flex gap-2 flex-wrap">
                            {meetingDetail.analysis.themes.map((t, i) => (
                              <span key={i} className="text-xs bg-ag3ntwerk-accent/20 text-ag3ntwerk-accent px-2 py-1 rounded">
                                {t}
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Questions */}
                        {meetingDetail.analysis.questions.length > 0 && (
                          <div>
                            <h3 className="text-sm font-semibold text-ag3ntwerk-text mb-1">Questions</h3>
                            <ul className="space-y-1">
                              {meetingDetail.analysis.questions.map((q, i) => (
                                <li key={i} className="text-sm text-ag3ntwerk-muted flex items-start gap-2">
                                  {q.answered
                                    ? <CheckCircle size={14} className="text-ag3ntwerk-success mt-0.5 shrink-0" />
                                    : <AlertCircle size={14} className="text-yellow-400 mt-0.5 shrink-0" />
                                  }
                                  <div>
                                    <span>{q.question}</span>
                                    {q.answer && <span className="block text-xs text-ag3ntwerk-muted/70 mt-0.5">{q.answer}</span>}
                                  </div>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </>
                    )}

                    {/* Transcript (collapsible) */}
                    {meetingDetail.transcript_text && (
                      <details className="group">
                        <summary className="text-sm font-semibold text-ag3ntwerk-text cursor-pointer flex items-center gap-1">
                          <FileText size={14} /> Transcript
                        </summary>
                        <pre className="mt-2 text-xs text-ag3ntwerk-muted bg-ag3ntwerk-surface rounded p-3 max-h-64 overflow-auto whitespace-pre-wrap">
                          {meetingDetail.transcript_text}
                        </pre>
                      </details>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      )}

      {/* Action Items Tab */}
      {activeTab === 'action-items' && (
        <div>
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setStatusFilter('')}
              className={`text-xs px-3 py-1 rounded ${!statusFilter ? 'bg-ag3ntwerk-accent text-white' : 'bg-ag3ntwerk-surface text-ag3ntwerk-muted'}`}
            >
              All
            </button>
            {statusOptions.map(s => (
              <button
                key={s}
                onClick={() => setStatusFilter(s)}
                className={`text-xs px-3 py-1 rounded ${statusFilter === s ? 'bg-ag3ntwerk-accent text-white' : 'bg-ag3ntwerk-surface text-ag3ntwerk-muted'}`}
              >
                {s.replace('_', ' ')}
              </button>
            ))}
          </div>

          {filteredItems.length === 0 ? (
            <div className="text-center text-ag3ntwerk-muted py-12">
              <ListChecks size={48} className="mx-auto mb-4 opacity-30" />
              <p>No action items{statusFilter ? ` with status "${statusFilter}"` : ''}.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredItems.map(item => (
                <div key={item.id} className="bg-ag3ntwerk-card rounded-lg border border-ag3ntwerk-border p-4 flex items-center justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className={`text-xs font-semibold ${priorityColor(item.priority)}`}>
                        {item.priority.toUpperCase()}
                      </span>
                      <span className="text-sm text-ag3ntwerk-text truncate">{item.description}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-ag3ntwerk-muted mt-1">
                      {item.assignee && <span>Assigned: {item.assignee}</span>}
                      {item.deadline && <span>Due: {new Date(item.deadline).toLocaleDateString()}</span>}
                    </div>
                  </div>
                  <select
                    value={item.status}
                    onChange={(e) => handleStatusChange(item.id, e.target.value)}
                    className="ml-4 text-xs bg-ag3ntwerk-surface border border-ag3ntwerk-border rounded px-2 py-1 text-ag3ntwerk-text"
                  >
                    {statusOptions.map(s => (
                      <option key={s} value={s}>{s.replace('_', ' ')}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Themes Tab */}
      {activeTab === 'themes' && (
        <div>
          {themes.length === 0 ? (
            <div className="text-center text-ag3ntwerk-muted py-12">
              <Tag size={48} className="mx-auto mb-4 opacity-30" />
              <p>No themes detected yet. Process some meetings first.</p>
            </div>
          ) : (
            <div className="space-y-2">
              {themes.map(t => (
                <div key={t.theme} className="flex items-center gap-3">
                  <span className="text-sm text-ag3ntwerk-text w-32 truncate">{t.theme}</span>
                  <div className="flex-1 bg-ag3ntwerk-surface rounded-full h-4 overflow-hidden">
                    <div
                      className="bg-ag3ntwerk-accent h-full rounded-full transition-all"
                      style={{ width: `${(t.count / maxThemeCount) * 100}%` }}
                    />
                  </div>
                  <span className="text-xs text-ag3ntwerk-muted w-8 text-right">{t.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
