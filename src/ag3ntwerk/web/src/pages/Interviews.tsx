import { useEffect, useState } from 'react'
import {
  Mic,
  FileText,
  Play,
  Plus,
  ChevronRight,
  Clock,
  CheckCircle,
  XCircle,
  Send,
  Trash2,
  RefreshCw,
  Keyboard,
  Volume2,
} from 'lucide-react'
import VoiceRecorder from '../components/VoiceRecorder'

interface InterviewScript {
  id: string
  topic: string
  description: string
  question_count: number
}

interface InterviewSession {
  id: string
  topic: string
  status: string
  current_question_index: number
  total_questions: number
  current_question: string | null
  progress: number
  answers_count: number
  started_at: string | null
  completed_at: string | null
}

interface InterviewResult {
  session_id: string
  topic: string
  answers_count: number
  duration_seconds: number
}

const API_BASE = '/api/v1/interviews'

export default function Interviews() {
  const [scripts, setScripts] = useState<InterviewScript[]>([])
  const [sessions, setSessions] = useState<InterviewSession[]>([])
  const [results, setResults] = useState<InterviewResult[]>([])
  const [activeSession, setActiveSession] = useState<InterviewSession | null>(null)
  const [showCreateScript, setShowCreateScript] = useState(false)
  const [currentAnswer, setCurrentAnswer] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [inputMode, setInputMode] = useState<'text' | 'voice'>('voice')

  useEffect(() => {
    fetchScripts()
    fetchSessions()
    fetchResults()
  }, [])

  const fetchScripts = async () => {
    try {
      const res = await fetch(`${API_BASE}/scripts`)
      if (res.ok) {
        const data = await res.json()
        setScripts(data.scripts || [])
      }
    } catch (e) {
      console.error('Failed to fetch scripts:', e)
    }
  }

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_BASE}/sessions`)
      if (res.ok) {
        const data = await res.json()
        setSessions(data.sessions || [])
      }
    } catch (e) {
      console.error('Failed to fetch sessions:', e)
    }
  }

  const fetchResults = async () => {
    try {
      const res = await fetch(`${API_BASE}/results`)
      if (res.ok) {
        const data = await res.json()
        setResults(data.results || [])
      }
    } catch (e) {
      console.error('Failed to fetch results:', e)
    }
  }

  const startSession = async (scriptId: string) => {
    try {
      const formData = new FormData()
      formData.append('script_id', scriptId)
      const res = await fetch(`${API_BASE}/sessions`, {
        method: 'POST',
        body: formData,
      })
      if (res.ok) {
        const session = await res.json()
        setActiveSession(session)
        fetchSessions()
      }
    } catch (e) {
      console.error('Failed to start session:', e)
    }
  }

  const submitAnswer = async () => {
    if (!activeSession || !currentAnswer.trim()) return

    setIsSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/sessions/${activeSession.id}/answer`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: currentAnswer }),
      })
      if (res.ok) {
        const updated = await res.json()
        setActiveSession(updated)
        setCurrentAnswer('')
        fetchSessions()
      }
    } catch (e) {
      console.error('Failed to submit answer:', e)
    }
    setIsSubmitting(false)
  }

  const finishSession = async () => {
    if (!activeSession) return

    try {
      const res = await fetch(`${API_BASE}/sessions/${activeSession.id}/finish`, {
        method: 'POST',
      })
      if (res.ok) {
        setActiveSession(null)
        fetchSessions()
        fetchResults()
      }
    } catch (e) {
      console.error('Failed to finish session:', e)
    }
  }

  const cancelSession = async () => {
    if (!activeSession) return

    try {
      const res = await fetch(`${API_BASE}/sessions/${activeSession.id}/cancel`, {
        method: 'POST',
      })
      if (res.ok) {
        setActiveSession(null)
        fetchSessions()
      }
    } catch (e) {
      console.error('Failed to cancel session:', e)
    }
  }

  const deleteScript = async (scriptId: string) => {
    try {
      const res = await fetch(`${API_BASE}/scripts/${scriptId}`, {
        method: 'DELETE',
      })
      if (res.ok) {
        fetchScripts()
      }
    } catch (e) {
      console.error('Failed to delete script:', e)
    }
  }

  // Active Interview View
  if (activeSession && activeSession.status === 'in_progress') {
    return (
      <div className="p-8">
        <div className="max-w-3xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-2xl font-bold text-aw-text">{activeSession.topic}</h1>
              <p className="text-aw-muted mt-1">
                Question {activeSession.current_question_index + 1} of {activeSession.total_questions}
              </p>
            </div>
            <button
              onClick={cancelSession}
              className="flex items-center gap-2 px-4 py-2 text-aw-error hover:bg-aw-error/10 rounded-lg transition-colors"
            >
              <XCircle size={18} />
              Cancel
            </button>
          </div>

          {/* Progress Bar */}
          <div className="mb-8">
            <div className="h-2 bg-aw-card rounded-full overflow-hidden">
              <div
                className="h-full bg-aw-accent rounded-full transition-all"
                style={{ width: `${activeSession.progress * 100}%` }}
              />
            </div>
          </div>

          {/* Current Question */}
          {activeSession.current_question && (
            <div className="bg-aw-surface rounded-xl border border-aw-border p-6 mb-6">
              <div className="flex items-start gap-4">
                <div className="p-3 rounded-lg bg-aw-accent/10">
                  <Mic size={24} className="text-aw-accent" />
                </div>
                <div>
                  <p className="text-lg text-aw-text">{activeSession.current_question}</p>
                </div>
              </div>
            </div>
          )}

          {/* Input Mode Toggle */}
          <div className="flex items-center justify-center gap-2 mb-4">
            <button
              onClick={() => setInputMode('voice')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                inputMode === 'voice'
                  ? 'bg-aw-accent text-white'
                  : 'bg-aw-card text-aw-muted hover:text-aw-text'
              }`}
            >
              <Volume2 size={18} />
              Voice
            </button>
            <button
              onClick={() => setInputMode('text')}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
                inputMode === 'text'
                  ? 'bg-aw-accent text-white'
                  : 'bg-aw-card text-aw-muted hover:text-aw-text'
              }`}
            >
              <Keyboard size={18} />
              Text
            </button>
          </div>

          {/* Answer Input */}
          <div className="bg-aw-surface rounded-xl border border-aw-border p-6">
            {inputMode === 'voice' ? (
              <div className="py-8">
                <VoiceRecorder
                  sessionId={activeSession.id}
                  onTranscription={(text, _duration) => {
                    setCurrentAnswer(text)
                    // Optionally auto-submit after voice transcription
                  }}
                  onError={(error) => {
                    console.error('Voice recording error:', error)
                    // Fall back to text input on error
                    setInputMode('text')
                  }}
                  disabled={isSubmitting}
                />
                {currentAnswer && (
                  <div className="mt-6 p-4 bg-aw-card rounded-lg border border-aw-border">
                    <p className="text-sm text-aw-muted mb-2">Transcription:</p>
                    <p className="text-aw-text">{currentAnswer}</p>
                  </div>
                )}
              </div>
            ) : (
              <textarea
                value={currentAnswer}
                onChange={(e) => setCurrentAnswer(e.target.value)}
                placeholder="Type your answer here..."
                className="w-full h-40 p-4 bg-aw-card border border-aw-border rounded-lg text-aw-text placeholder-aw-muted resize-none focus:outline-none focus:border-aw-accent"
              />
            )}
            <div className="flex justify-between mt-4">
              <p className="text-sm text-aw-muted">
                {currentAnswer.length} characters
              </p>
              <div className="flex gap-3">
                {!activeSession.current_question && (
                  <button
                    onClick={finishSession}
                    className="flex items-center gap-2 px-6 py-2 bg-aw-success text-white rounded-lg hover:bg-green-600"
                  >
                    <CheckCircle size={18} />
                    Finish Interview
                  </button>
                )}
                <button
                  onClick={submitAnswer}
                  disabled={!currentAnswer.trim() || isSubmitting}
                  className="flex items-center gap-2 px-6 py-2 bg-aw-accent text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <Send size={18} />
                  {isSubmitting ? 'Submitting...' : 'Submit Answer'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-aw-text">Interview Manager</h1>
          <p className="text-aw-muted mt-1">
            AI-guided interviews for expertise extraction
          </p>
        </div>
        <button
          onClick={() => setShowCreateScript(true)}
          className="flex items-center gap-2 px-4 py-2 bg-aw-accent text-white rounded-lg hover:bg-indigo-600"
        >
          <Plus size={20} />
          New Script
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Scripts */}
        <div className="lg:col-span-2 space-y-6">
          <section className="bg-aw-surface rounded-xl border border-aw-border p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-aw-text flex items-center gap-2">
                <FileText size={20} className="text-aw-accent" />
                Interview Scripts
              </h2>
              <button
                onClick={fetchScripts}
                className="text-aw-muted hover:text-aw-text"
              >
                <RefreshCw size={18} />
              </button>
            </div>

            {scripts.length > 0 ? (
              <div className="space-y-3">
                {scripts.map((script) => (
                  <div
                    key={script.id}
                    className="flex items-center justify-between bg-aw-card rounded-lg p-4"
                  >
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-aw-text">{script.topic}</h3>
                      <p className="text-sm text-aw-muted">
                        {script.question_count} questions
                        {script.description && ` • ${script.description}`}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => startSession(script.id)}
                        className="flex items-center gap-1 px-3 py-1.5 bg-aw-accent text-white text-sm rounded-lg hover:bg-indigo-600"
                      >
                        <Play size={14} />
                        Start
                      </button>
                      <button
                        onClick={() => deleteScript(script.id)}
                        className="p-1.5 text-aw-muted hover:text-aw-error rounded"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <FileText size={48} className="mx-auto mb-2 text-aw-muted opacity-50" />
                <p className="text-aw-muted">No interview scripts yet</p>
                <p className="text-sm text-aw-muted mt-1">
                  Create a script to start conducting interviews
                </p>
              </div>
            )}
          </section>

          {/* Recent Sessions */}
          <section className="bg-aw-surface rounded-xl border border-aw-border p-6">
            <h2 className="text-lg font-semibold text-aw-text flex items-center gap-2 mb-4">
              <Clock size={20} className="text-aw-warning" />
              Recent Sessions
            </h2>

            {sessions.length > 0 ? (
              <div className="space-y-3">
                {sessions.slice(0, 5).map((session) => (
                  <div
                    key={session.id}
                    className="flex items-center gap-3 bg-aw-card rounded-lg p-4"
                  >
                    <StatusIcon status={session.status} />
                    <div className="flex-1 min-w-0">
                      <h3 className="font-medium text-aw-text">{session.topic}</h3>
                      <p className="text-sm text-aw-muted">
                        {session.answers_count} of {session.total_questions} answered
                        {session.completed_at && ` • Completed`}
                      </p>
                    </div>
                    {session.status === 'in_progress' && (
                      <button
                        onClick={() => setActiveSession(session)}
                        className="flex items-center gap-1 text-aw-accent text-sm hover:underline"
                      >
                        Continue
                        <ChevronRight size={14} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <Clock size={48} className="mx-auto mb-2 text-aw-muted opacity-50" />
                <p className="text-aw-muted">No interview sessions yet</p>
              </div>
            )}
          </section>
        </div>

        {/* Results */}
        <div className="space-y-6">
          <section className="bg-aw-surface rounded-xl border border-aw-border p-6">
            <h2 className="text-lg font-semibold text-aw-text flex items-center gap-2 mb-4">
              <CheckCircle size={20} className="text-aw-success" />
              Completed Interviews
            </h2>

            {results.length > 0 ? (
              <div className="space-y-3">
                {results.map((result) => (
                  <div
                    key={result.session_id}
                    className="bg-aw-card rounded-lg p-4"
                  >
                    <h3 className="font-medium text-aw-text">{result.topic}</h3>
                    <p className="text-sm text-aw-muted mt-1">
                      {result.answers_count} answers
                      {result.duration_seconds > 0 &&
                        ` • ${Math.round(result.duration_seconds / 60)} min`}
                    </p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <CheckCircle size={48} className="mx-auto mb-2 text-aw-muted opacity-50" />
                <p className="text-aw-muted">No completed interviews</p>
              </div>
            )}
          </section>

          {/* Quick Actions */}
          <section className="bg-aw-surface rounded-xl border border-aw-border p-6">
            <h2 className="text-lg font-semibold text-aw-text mb-4">Quick Actions</h2>
            <div className="space-y-2">
              <button
                onClick={() => setShowCreateScript(true)}
                className="w-full flex items-center gap-3 p-3 bg-aw-card rounded-lg hover:bg-aw-accent/10 transition-colors"
              >
                <Plus size={18} className="text-aw-accent" />
                <span className="text-aw-text">Create Script</span>
              </button>
              <button
                onClick={() => {
                  fetchScripts()
                  fetchSessions()
                  fetchResults()
                }}
                className="w-full flex items-center gap-3 p-3 bg-aw-card rounded-lg hover:bg-aw-accent/10 transition-colors"
              >
                <RefreshCw size={18} className="text-aw-muted" />
                <span className="text-aw-text">Refresh All</span>
              </button>
            </div>
          </section>
        </div>
      </div>

      {/* Create Script Modal */}
      {showCreateScript && (
        <CreateScriptModal
          onClose={() => setShowCreateScript(false)}
          onCreated={() => {
            setShowCreateScript(false)
            fetchScripts()
          }}
        />
      )}
    </div>
  )
}

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'in_progress':
      return <Clock size={18} className="text-aw-warning" />
    case 'completed':
      return <CheckCircle size={18} className="text-aw-success" />
    case 'cancelled':
      return <XCircle size={18} className="text-aw-error" />
    default:
      return <Clock size={18} className="text-aw-muted" />
  }
}

function CreateScriptModal({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: () => void
}) {
  const [topic, setTopic] = useState('')
  const [description, setDescription] = useState('')
  const [questions, setQuestions] = useState<string[]>([''])
  const [isSubmitting, setIsSubmitting] = useState(false)

  const addQuestion = () => {
    setQuestions([...questions, ''])
  }

  const updateQuestion = (index: number, text: string) => {
    const updated = [...questions]
    updated[index] = text
    setQuestions(updated)
  }

  const removeQuestion = (index: number) => {
    if (questions.length > 1) {
      setQuestions(questions.filter((_, i) => i !== index))
    }
  }

  const handleSubmit = async () => {
    if (!topic.trim() || questions.every((q) => !q.trim())) return

    setIsSubmitting(true)
    try {
      const res = await fetch(`${API_BASE}/scripts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic.trim(),
          description: description.trim(),
          questions: questions
            .filter((q) => q.trim())
            .map((text) => ({ text: text.trim(), topic: '' })),
        }),
      })
      if (res.ok) {
        onCreated()
      }
    } catch (e) {
      console.error('Failed to create script:', e)
    }
    setIsSubmitting(false)
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-aw-surface rounded-xl border border-aw-border p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
        <h2 className="text-xl font-semibold text-aw-text mb-4">Create Interview Script</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-aw-muted mb-1">Topic</label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g., AI Scaling Strategies"
              className="w-full p-3 bg-aw-card border border-aw-border rounded-lg text-aw-text placeholder-aw-muted focus:outline-none focus:border-aw-accent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-aw-muted mb-1">
              Description (optional)
            </label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description of the interview"
              className="w-full p-3 bg-aw-card border border-aw-border rounded-lg text-aw-text placeholder-aw-muted focus:outline-none focus:border-aw-accent"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-aw-muted mb-2">Questions</label>
            <div className="space-y-2">
              {questions.map((q, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    type="text"
                    value={q}
                    onChange={(e) => updateQuestion(i, e.target.value)}
                    placeholder={`Question ${i + 1}`}
                    className="flex-1 p-3 bg-aw-card border border-aw-border rounded-lg text-aw-text placeholder-aw-muted focus:outline-none focus:border-aw-accent"
                  />
                  {questions.length > 1 && (
                    <button
                      onClick={() => removeQuestion(i)}
                      className="p-3 text-aw-muted hover:text-aw-error"
                    >
                      <Trash2 size={18} />
                    </button>
                  )}
                </div>
              ))}
            </div>
            <button
              onClick={addQuestion}
              className="mt-2 flex items-center gap-1 text-aw-accent text-sm hover:underline"
            >
              <Plus size={14} />
              Add Question
            </button>
          </div>
        </div>

        <div className="flex justify-end gap-3 mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-aw-card border border-aw-border text-aw-text rounded-lg hover:bg-aw-surface"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!topic.trim() || questions.every((q) => !q.trim()) || isSubmitting}
            className="px-4 py-2 bg-aw-accent text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50"
          >
            {isSubmitting ? 'Creating...' : 'Create Script'}
          </button>
        </div>
      </div>
    </div>
  )
}
