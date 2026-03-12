import { create } from 'zustand'

interface Task {
  id: string
  description: string
  task_type: string
  status: string
  priority: string
  result?: string | { content?: string; [key: string]: unknown }
  routed_to?: string
  context?: Record<string, unknown>
  created_at?: string
}

interface Milestone {
  id: string
  title: string
  status: string
}

interface Goal {
  id: string
  title: string
  description?: string
  status: string
  progress: number
  milestones: Milestone[]
  created_at?: string
}

interface Executive {
  code: string
  codename: string
  available: boolean
  description?: string
}

interface COOStatus {
  state: string
  mode: string
  codename?: string
  total_tasks_executed?: number
  uptime_seconds?: number
  successful_executions?: number
  failed_executions?: number
  daily_spend_usd?: number
  pending_approvals?: number
}

interface DashboardStats {
  tasks: { total: number; active: number; completed: number }
  goals: { total: number; active: number }
  memory: { total_chunks?: number }
  knowledge: { total_entities?: number; total_facts?: number }
  decisions: { total: number }
  coo?: COOStatus
}

interface WSMessage {
  type: string
  data: unknown
  timestamp: string
}

interface Store {
  // Connection state
  connected: boolean
  ws: WebSocket | null

  // Data
  tasks: Task[]
  executives: Executive[]
  cooStatus: COOStatus | null
  dashboardStats: DashboardStats | null
  goals: Goal[]

  // Activity feed
  activities: WSMessage[]

  // Actions
  connect: () => void
  disconnect: () => void

  // API calls
  fetchDashboardStats: () => Promise<void>
  fetchTasks: () => Promise<void>
  fetchExecutives: () => Promise<void>
  fetchCOOStatus: () => Promise<void>
  fetchGoals: () => Promise<void>

  // Task actions
  createTask: (task: { description: string; task_type?: string; priority?: string }) => Promise<Task | null>

  // Goal actions
  createGoal: (goal: { title: string; description?: string }) => Promise<Goal | null>
  updateGoal: (goalId: string, updates: { title?: string; description?: string; status?: string; progress?: number }) => Promise<Goal | null>
  addMilestone: (goalId: string, title: string) => Promise<Milestone | null>
  updateMilestone: (goalId: string, milestoneId: string, status: string) => Promise<Milestone | null>

  // COO actions
  startCOO: () => Promise<boolean>
  stopCOO: () => Promise<boolean>
  setCOOMode: (mode: string) => Promise<boolean>
  approveSuggestion: (suggestionId: string) => Promise<boolean>
  rejectSuggestion: (suggestionId: string) => Promise<boolean>

  // Chat
  sendChat: (message: string, executive?: string, conversationId?: string) => Promise<{ content: string; executive: string; error?: boolean; conversation_id?: string }>
  listConversations: () => Promise<{ id: string; executive: string; message_count: number; preview: string; updated_at: string }[]>
  deleteConversation: (conversationId: string) => Promise<boolean>
}

const API_BASE = '/api/v1'

let wsReconnectAttempts = 0
const WS_MAX_RECONNECT_ATTEMPTS = 10
const WS_BASE_RECONNECT_DELAY = 1000

export const useStore = create<Store>((set, get) => ({
  connected: false,
  ws: null,
  tasks: [],
  executives: [],
  cooStatus: null,
  dashboardStats: null,
  goals: [],
  activities: [],

  connect: () => {
    // Prevent duplicate connections
    const existing = get().ws
    if (existing && (existing.readyState === WebSocket.OPEN || existing.readyState === WebSocket.CONNECTING)) {
      return
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws`)

    ws.onopen = () => {
      set({ connected: true, ws })
      wsReconnectAttempts = 0
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data)

        // Add to activity feed
        set((state) => ({
          activities: [message, ...state.activities].slice(0, 50)
        }))

        // Handle specific event types
        switch (message.type) {
          case 'task_created':
          case 'task_updated':
          case 'task_completed':
          case 'task_failed':
            get().fetchTasks()
            get().fetchDashboardStats()
            break
          case 'coo_started':
          case 'coo_stopped':
          case 'coo_mode_changed':
            get().fetchCOOStatus()
            get().fetchDashboardStats()
            break
          case 'goal_created':
          case 'goal_updated':
          case 'milestone_added':
          case 'milestone_updated':
            get().fetchGoals()
            get().fetchDashboardStats()
            break
        }
      } catch (e) {
        console.error('Failed to parse WS message:', e)
      }
    }

    ws.onclose = () => {
      set({ connected: false, ws: null })
      // Exponential backoff reconnect with max attempts
      if (wsReconnectAttempts < WS_MAX_RECONNECT_ATTEMPTS) {
        const delay = WS_BASE_RECONNECT_DELAY * Math.pow(2, wsReconnectAttempts)
        wsReconnectAttempts++
        console.log(`WebSocket disconnected. Reconnecting in ${delay / 1000}s (attempt ${wsReconnectAttempts}/${WS_MAX_RECONNECT_ATTEMPTS})`)
        setTimeout(() => get().connect(), delay)
      } else {
        console.warn('WebSocket max reconnect attempts reached. Refresh the page to reconnect.')
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  },

  disconnect: () => {
    const { ws } = get()
    if (ws) {
      ws.close()
      set({ connected: false, ws: null })
    }
  },

  fetchDashboardStats: async () => {
    try {
      const res = await fetch(`${API_BASE}/dashboard/stats`)
      if (res.ok) {
        const data = await res.json()
        set({ dashboardStats: data, cooStatus: data.coo })
      }
    } catch (e) {
      console.error('Failed to fetch dashboard stats:', e)
    }
  },

  fetchTasks: async () => {
    try {
      const res = await fetch(`${API_BASE}/tasks`)
      if (res.ok) {
        const data = await res.json()
        // Normalize task results (extract content if it's a nested object)
        const tasks = (data.tasks || []).map((task: Task) => ({
          ...task,
          result: typeof task.result === 'object' && task.result?.content
            ? task.result.content
            : task.result,
        }))
        set({ tasks })
      }
    } catch (e) {
      console.error('Failed to fetch tasks:', e)
    }
  },

  fetchExecutives: async () => {
    try {
      const res = await fetch(`${API_BASE}/executives`)
      if (res.ok) {
        const data = await res.json()
        set({ executives: data.executives || [] })
      }
    } catch (e) {
      console.error('Failed to fetch executives:', e)
    }
  },

  fetchCOOStatus: async () => {
    try {
      const res = await fetch(`${API_BASE}/coo/status`)
      if (res.ok) {
        const data = await res.json()
        set({ cooStatus: data })
      }
    } catch (e) {
      console.error('Failed to fetch COO status:', e)
    }
  },

  fetchGoals: async () => {
    try {
      const res = await fetch(`${API_BASE}/goals`)
      if (res.ok) {
        const data = await res.json()
        set({ goals: data.goals || [] })
      }
    } catch (e) {
      console.error('Failed to fetch goals:', e)
    }
  },

  createTask: async (task) => {
    try {
      const res = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          description: task.description,
          task_type: task.task_type || 'general',
          priority: task.priority || 'medium',
          context: {},
        }),
      })
      if (res.ok) {
        const newTask = await res.json()
        get().fetchTasks()
        return newTask
      }
    } catch (e) {
      console.error('Failed to create task:', e)
    }
    return null
  },

  createGoal: async (goal) => {
    try {
      const res = await fetch(`${API_BASE}/goals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: goal.title,
          description: goal.description || null,
          milestones: [],
        }),
      })
      if (res.ok) {
        const newGoal = await res.json()
        get().fetchGoals()
        get().fetchDashboardStats()
        return newGoal
      }
    } catch (e) {
      console.error('Failed to create goal:', e)
    }
    return null
  },

  updateGoal: async (goalId, updates) => {
    try {
      const res = await fetch(`${API_BASE}/goals/${goalId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })
      if (res.ok) {
        const updatedGoal = await res.json()
        get().fetchGoals()
        return updatedGoal
      }
    } catch (e) {
      console.error('Failed to update goal:', e)
    }
    return null
  },

  addMilestone: async (goalId, title) => {
    try {
      const res = await fetch(`${API_BASE}/goals/${goalId}/milestones`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title }),
      })
      if (res.ok) {
        const data = await res.json()
        get().fetchGoals()
        return data.milestone
      }
    } catch (e) {
      console.error('Failed to add milestone:', e)
    }
    return null
  },

  updateMilestone: async (goalId, milestoneId, status) => {
    try {
      const res = await fetch(`${API_BASE}/goals/${goalId}/milestones/${milestoneId}?status=${status}`, {
        method: 'PUT',
      })
      if (res.ok) {
        const data = await res.json()
        get().fetchGoals()
        return data.milestone
      }
    } catch (e) {
      console.error('Failed to update milestone:', e)
    }
    return null
  },

  startCOO: async () => {
    try {
      const res = await fetch(`${API_BASE}/coo/start`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        get().fetchCOOStatus()
        get().fetchDashboardStats()
        return data.success
      }
    } catch (e) {
      console.error('Failed to start COO:', e)
    }
    return false
  },

  stopCOO: async () => {
    try {
      const res = await fetch(`${API_BASE}/coo/stop`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        get().fetchCOOStatus()
        get().fetchDashboardStats()
        return data.success
      }
    } catch (e) {
      console.error('Failed to stop COO:', e)
    }
    return false
  },

  setCOOMode: async (mode) => {
    try {
      const res = await fetch(`${API_BASE}/coo/mode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      })
      if (res.ok) {
        const data = await res.json()
        get().fetchCOOStatus()
        return data.success
      }
    } catch (e) {
      console.error('Failed to set COO mode:', e)
    }
    return false
  },

  approveSuggestion: async (suggestionId) => {
    try {
      const res = await fetch(`${API_BASE}/coo/suggestions/${suggestionId}/approve`, {
        method: 'POST',
      })
      if (res.ok) {
        const data = await res.json()
        get().fetchTasks()
        get().fetchCOOStatus()
        get().fetchDashboardStats()
        return data.success
      }
    } catch (e) {
      console.error('Failed to approve suggestion:', e)
    }
    return false
  },

  rejectSuggestion: async (suggestionId) => {
    try {
      const res = await fetch(`${API_BASE}/coo/suggestions/${suggestionId}/reject`, {
        method: 'POST',
      })
      if (res.ok) {
        const data = await res.json()
        return data.success
      }
    } catch (e) {
      console.error('Failed to reject suggestion:', e)
    }
    return false
  },

  sendChat: async (message, executive = 'COO', conversationId?) => {
    try {
      const body: Record<string, string> = { message, executive }
      if (conversationId) {
        body.conversation_id = conversationId
      }
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        const data = await res.json()
        // Handle nested content from COO response
        const content = typeof data.content === 'object' && data.content?.content
          ? data.content.content
          : data.content
        return {
          content: content || 'No response',
          executive: data.executive || executive,
          error: data.error,
          conversation_id: data.conversation_id,
        }
      }
      return { content: 'Request failed', executive, error: true }
    } catch (e) {
      console.error('Failed to send chat:', e)
      return { content: `Error: ${e}`, executive, error: true }
    }
  },

  listConversations: async () => {
    try {
      const res = await fetch(`${API_BASE}/conversations`)
      if (res.ok) {
        const data = await res.json()
        return data.conversations || []
      }
    } catch (e) {
      console.error('Failed to list conversations:', e)
    }
    return []
  },

  deleteConversation: async (conversationId) => {
    try {
      const res = await fetch(`${API_BASE}/conversations/${conversationId}`, {
        method: 'DELETE',
      })
      if (res.ok) {
        return true
      }
    } catch (e) {
      console.error('Failed to delete conversation:', e)
    }
    return false
  },
}))
