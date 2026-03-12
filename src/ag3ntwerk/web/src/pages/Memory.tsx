import { useState } from 'react'
import { useStore } from '../store'
import { Search, Database, Brain, Lightbulb, Clock } from 'lucide-react'

export default function Memory() {
  const { dashboardStats } = useStore()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<any[]>([])
  const [searching, setSearching] = useState(false)

  const handleSearch = async () => {
    if (!query.trim()) return
    setSearching(true)
    try {
      const res = await fetch(`/api/v1/memory/search?query=${encodeURIComponent(query)}&n_results=10`)
      if (res.ok) {
        const data = await res.json()
        setResults(data.results || [])
      }
    } catch (e) {
      console.error('Search failed:', e)
    }
    setSearching(false)
  }

  const stats = dashboardStats || {
    memory: { total_chunks: 0 },
    knowledge: { total_entities: 0, total_facts: 0 },
    decisions: { total: 0 },
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-aw-text">Memory & Knowledge</h1>
        <p className="text-aw-muted mt-1">Search and explore your knowledge base</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        <StatCard
          icon={Database}
          label="Memory Chunks"
          value={stats.memory.total_chunks || 0}
        />
        <StatCard
          icon={Brain}
          label="Entities"
          value={stats.knowledge.total_entities || 0}
        />
        <StatCard
          icon={Lightbulb}
          label="Facts"
          value={stats.knowledge.total_facts || 0}
        />
        <StatCard
          icon={Clock}
          label="Decisions"
          value={stats.decisions.total || 0}
        />
      </div>

      {/* Search */}
      <div className="bg-aw-surface rounded-xl border border-aw-border p-6 mb-6">
        <h2 className="text-xl font-semibold text-aw-text mb-4">Search Memory</h2>
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search
              size={20}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-aw-muted"
            />
            <input
              type="text"
              placeholder="Search your memory..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              className="w-full bg-aw-card border border-aw-border rounded-lg pl-12 pr-4 py-3 text-aw-text placeholder:text-aw-muted"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={searching}
            className="px-6 py-3 bg-aw-accent text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50 transition-colors"
          >
            {searching ? 'Searching...' : 'Search'}
          </button>
        </div>
      </div>

      {/* Results */}
      {results.length > 0 && (
        <div className="bg-aw-surface rounded-xl border border-aw-border p-6">
          <h2 className="text-xl font-semibold text-aw-text mb-4">
            Results ({results.length})
          </h2>
          <div className="space-y-4">
            {results.map((result, i) => (
              <div
                key={i}
                className="bg-aw-card rounded-lg p-4 border border-aw-border"
              >
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-aw-muted">
                    Score: {(result.score * 100).toFixed(1)}%
                  </span>
                  {result.metadata?.source && (
                    <span className="text-xs text-aw-muted bg-aw-surface px-2 py-1 rounded">
                      {result.metadata.source}
                    </span>
                  )}
                </div>
                <p className="text-aw-text">{result.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Empty state */}
      {query && results.length === 0 && !searching && (
        <div className="bg-aw-surface rounded-xl border border-aw-border p-8 text-center">
          <Database size={48} className="mx-auto mb-2 text-aw-muted opacity-50" />
          <p className="text-aw-muted">No results found for "{query}"</p>
        </div>
      )}
    </div>
  )
}

function StatCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType
  label: string
  value: number
}) {
  return (
    <div className="bg-aw-surface rounded-xl border border-aw-border p-4">
      <div className="flex items-center gap-2 text-aw-muted mb-2">
        <Icon size={16} />
        <span className="text-sm">{label}</span>
      </div>
      <p className="text-2xl font-bold text-aw-text">{value.toLocaleString()}</p>
    </div>
  )
}
