import { useState, useRef, useEffect } from 'react'
import { useStore } from '../store'
import { Send, Bot, User, Loader2, Users, Plus } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  executive?: string
  timestamp: Date
  error?: boolean
}

const EXECUTIVES = [
  { code: 'COO', name: 'COO (Nexus)', description: 'Central control & task routing' },
  { code: 'CTO', name: 'CTO (Forge)', description: 'Technology & development' },
  { code: 'CFO', name: 'CFO (Keystone)', description: 'Finance & budgeting' },
  { code: 'CIO', name: 'CIO (Sentinel)', description: 'Security & infrastructure' },
  { code: 'CDO', name: 'CDO (Index)', description: 'Data & analytics' },
  { code: 'CMO', name: 'CMO (Echo)', description: 'Marketing & communications' },
  { code: 'CSO', name: 'CSO (Compass)', description: 'Strategy & planning' },
]

export default function Chat() {
  const { sendChat, cooStatus } = useStore()
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedExecutive, setSelectedExecutive] = useState('COO')
  const [conversationId, setConversationId] = useState<string | undefined>(undefined)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const prevExecutiveRef = useRef(selectedExecutive)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Reset conversation when executive changes
  useEffect(() => {
    if (prevExecutiveRef.current !== selectedExecutive) {
      prevExecutiveRef.current = selectedExecutive
      setMessages([])
      setConversationId(undefined)
    }
  }, [selectedExecutive])

  const handleNewChat = () => {
    setMessages([])
    setConversationId(undefined)
  }

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      const response = await sendChat(input, selectedExecutive, conversationId)

      // Capture conversation_id from first response
      if (response.conversation_id && !conversationId) {
        setConversationId(response.conversation_id)
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        executive: response.executive,
        error: response.error,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (e) {
      console.error('Chat error:', e)
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Failed to connect to the server. Please check if the backend is running.',
          error: true,
          timestamp: new Date(),
        },
      ])
    }

    setLoading(false)
  }

  const cooReady = cooStatus?.state && cooStatus.state !== 'idle' && cooStatus.state !== 'not_available' && cooStatus.state !== 'unknown'

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-6 border-b border-csuite-border">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-csuite-text">Executive Chat</h1>
            <p className="text-csuite-muted">
              Talk to your C-Suite executives
              {!cooReady && ' (COO offline)'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            {/* New Chat button */}
            <button
              onClick={handleNewChat}
              className="flex items-center gap-1.5 px-3 py-2 text-sm bg-csuite-surface border border-csuite-border rounded-lg text-csuite-text hover:border-csuite-accent/50 transition-colors"
            >
              <Plus size={16} />
              New Chat
            </button>
            {/* Executive Selector */}
            <div className="flex items-center gap-2">
              <Users size={20} className="text-csuite-muted" />
              <select
                value={selectedExecutive}
                onChange={(e) => setSelectedExecutive(e.target.value)}
                className="bg-csuite-surface border border-csuite-border rounded-lg px-3 py-2 text-csuite-text"
              >
                {EXECUTIVES.map((exec) => (
                  <option key={exec.code} value={exec.code}>
                    {exec.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {messages.length === 0 && (
            <div className="text-center py-12">
              <Bot size={48} className="mx-auto mb-4 text-csuite-muted opacity-50" />
              <h2 className="text-xl font-semibold text-csuite-text mb-2">
                Welcome to C-Suite Chat
              </h2>
              <p className="text-csuite-muted mb-4">
                Select an executive and start a conversation.
              </p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3 max-w-lg mx-auto">
                {EXECUTIVES.slice(0, 6).map((exec) => (
                  <button
                    key={exec.code}
                    onClick={() => setSelectedExecutive(exec.code)}
                    className={`p-3 rounded-lg border text-left transition-colors ${
                      selectedExecutive === exec.code
                        ? 'border-csuite-accent bg-csuite-accent/10'
                        : 'border-csuite-border bg-csuite-surface hover:border-csuite-accent/50'
                    }`}
                  >
                    <p className="font-medium text-csuite-text text-sm">{exec.code}</p>
                    <p className="text-xs text-csuite-muted">{exec.description}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex gap-4 ${
                message.role === 'user' ? 'justify-end' : ''
              }`}
            >
              {message.role === 'assistant' && (
                <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
                  message.error ? 'bg-csuite-error' : 'bg-csuite-accent'
                }`}>
                  <Bot size={20} className="text-white" />
                </div>
              )}

              <div
                className={`flex-1 max-w-2xl ${
                  message.role === 'user' ? 'text-right' : ''
                }`}
              >
                <div
                  className={`inline-block rounded-2xl px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-csuite-accent text-white'
                      : message.error
                      ? 'bg-csuite-error/10 border border-csuite-error/30 text-csuite-text'
                      : 'bg-csuite-surface border border-csuite-border text-csuite-text'
                  }`}
                >
                  <p className="whitespace-pre-wrap">{message.content}</p>
                </div>

                {/* Executive badge for assistant messages */}
                {message.role === 'assistant' && message.executive && (
                  <div className="mt-2 text-xs text-csuite-muted">
                    via {message.executive}
                  </div>
                )}
              </div>

              {message.role === 'user' && (
                <div className="w-10 h-10 rounded-full bg-csuite-card flex items-center justify-center flex-shrink-0">
                  <User size={20} className="text-csuite-text" />
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div className="flex gap-4">
              <div className="w-10 h-10 rounded-full bg-csuite-accent flex items-center justify-center">
                <Loader2 size={20} className="text-white animate-spin" />
              </div>
              <div className="bg-csuite-surface border border-csuite-border rounded-2xl px-4 py-3">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-csuite-muted rounded-full animate-bounce" />
                  <span className="w-2 h-2 bg-csuite-muted rounded-full animate-bounce" style={{ animationDelay: '0.1s' }} />
                  <span className="w-2 h-2 bg-csuite-muted rounded-full animate-bounce" style={{ animationDelay: '0.2s' }} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input */}
      <div className="p-6 border-t border-csuite-border">
        <div className="max-w-3xl mx-auto flex gap-3">
          <input
            type="text"
            placeholder={`Ask ${selectedExecutive}...`}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            disabled={loading}
            className="flex-1 bg-csuite-surface border border-csuite-border rounded-xl px-4 py-3 text-csuite-text placeholder:text-csuite-muted disabled:opacity-50"
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="px-6 py-3 bg-csuite-accent text-white rounded-xl hover:bg-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={20} />
          </button>
        </div>
      </div>
    </div>
  )
}
