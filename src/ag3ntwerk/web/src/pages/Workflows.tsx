import { useEffect, useState } from 'react'
import {
  Play,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  GitBranch,
  Users,
  RefreshCw,
} from 'lucide-react'

interface WorkflowStep {
  name: string
  executive: string
  task_type: string
  description: string
  required: boolean
  depends_on: string[]
}

interface Workflow {
  name: string
  description: string
  class?: string
  steps?: WorkflowStep[]
  step_count?: number
}

interface WorkflowExecution {
  workflow_id: string
  workflow_name: string
  status: string
  success: boolean
  steps: {
    name: string
    status: string
    executive: string
    result?: unknown
    error?: string
  }[]
  output: Record<string, unknown>
  error?: string
  started_at: string
  completed_at: string
  duration_seconds?: number
}

const WORKFLOW_PARAMS: Record<string, { label: string; fields: { name: string; label: string; type: string; placeholder?: string }[] }> = {
  // Original workflows
  product_launch: {
    label: 'Product Launch',
    fields: [
      { name: 'product_name', label: 'Product Name', type: 'text', placeholder: 'e.g., GozerAI Pro' },
      { name: 'target_market', label: 'Target Market', type: 'text', placeholder: 'e.g., Enterprise developers' },
      { name: 'features', label: 'Features (comma-separated)', type: 'text', placeholder: 'e.g., AI chat, Code generation, Analytics' },
    ],
  },
  incident_response: {
    label: 'Incident Response',
    fields: [
      { name: 'incident_id', label: 'Incident ID', type: 'text', placeholder: 'e.g., INC-001' },
      { name: 'incident_type', label: 'Incident Type', type: 'text', placeholder: 'e.g., service_outage, security_breach' },
      { name: 'description', label: 'Description', type: 'text', placeholder: 'Describe the incident...' },
      { name: 'severity', label: 'Severity', type: 'select', placeholder: 'medium' },
    ],
  },
  budget_approval: {
    label: 'Budget Approval',
    fields: [
      { name: 'request_id', label: 'Request ID', type: 'text', placeholder: 'e.g., BUD-001' },
      { name: 'amount', label: 'Amount ($)', type: 'number', placeholder: 'e.g., 50000' },
      { name: 'purpose', label: 'Purpose', type: 'text', placeholder: 'e.g., New infrastructure investment' },
      { name: 'department', label: 'Department', type: 'text', placeholder: 'e.g., Engineering' },
    ],
  },
  feature_release: {
    label: 'Feature Release',
    fields: [
      { name: 'feature_name', label: 'Feature Name', type: 'text', placeholder: 'e.g., Dark Mode' },
      { name: 'feature_id', label: 'Feature ID', type: 'text', placeholder: 'e.g., FEAT-001' },
      { name: 'description', label: 'Description', type: 'text', placeholder: 'Describe the feature...' },
      { name: 'version', label: 'Version', type: 'text', placeholder: 'e.g., 2.1.0' },
    ],
  },
  // New workflows
  strategic_planning: {
    label: 'Strategic Planning',
    fields: [
      { name: 'initiative_name', label: 'Initiative Name', type: 'text', placeholder: 'e.g., Q3 Expansion Plan' },
      { name: 'planning_horizon', label: 'Planning Horizon', type: 'text', placeholder: 'e.g., 12 months' },
      { name: 'focus_areas', label: 'Focus Areas (comma-separated)', type: 'text', placeholder: 'e.g., growth, efficiency, innovation' },
      { name: 'budget_constraint', label: 'Budget Constraint ($)', type: 'number', placeholder: 'e.g., 5000000' },
    ],
  },
  security_audit: {
    label: 'Security Audit',
    fields: [
      { name: 'audit_name', label: 'Audit Name', type: 'text', placeholder: 'e.g., Q3 Security Review' },
      { name: 'scope', label: 'Audit Scope', type: 'text', placeholder: 'e.g., infrastructure, applications, data' },
      { name: 'compliance_frameworks', label: 'Compliance Frameworks (comma-separated)', type: 'text', placeholder: 'e.g., SOC2, GDPR, HIPAA' },
      { name: 'priority_systems', label: 'Priority Systems (comma-separated)', type: 'text', placeholder: 'e.g., payment, auth, customer-data' },
    ],
  },
  customer_onboarding: {
    label: 'Customer Onboarding',
    fields: [
      { name: 'customer_name', label: 'Customer Name', type: 'text', placeholder: 'e.g., Acme Corp' },
      { name: 'customer_tier', label: 'Customer Tier', type: 'text', placeholder: 'e.g., enterprise, premium, standard' },
      { name: 'products', label: 'Products (comma-separated)', type: 'text', placeholder: 'e.g., Platform Pro, Analytics Suite' },
      { name: 'timeline', label: 'Timeline', type: 'text', placeholder: 'e.g., 30 days' },
    ],
  },
  data_quality: {
    label: 'Data Quality Review',
    fields: [
      { name: 'review_name', label: 'Review Name', type: 'text', placeholder: 'e.g., Customer Data Quality Check' },
      { name: 'data_domains', label: 'Data Domains (comma-separated)', type: 'text', placeholder: 'e.g., customer, product, transaction' },
      { name: 'quality_metrics', label: 'Quality Metrics (comma-separated)', type: 'text', placeholder: 'e.g., completeness, accuracy, freshness' },
      { name: 'threshold', label: 'Quality Threshold (%)', type: 'number', placeholder: 'e.g., 95' },
    ],
  },
  revenue_growth: {
    label: 'Revenue Growth Initiative',
    fields: [
      { name: 'initiative_name', label: 'Initiative Name', type: 'text', placeholder: 'e.g., Q4 Revenue Push' },
      { name: 'target_increase', label: 'Target Increase (%)', type: 'number', placeholder: 'e.g., 20' },
      { name: 'focus_segments', label: 'Focus Segments (comma-separated)', type: 'text', placeholder: 'e.g., enterprise, mid-market, SMB' },
      { name: 'timeline', label: 'Timeline', type: 'text', placeholder: 'e.g., 90 days' },
    ],
  },
  compliance_audit: {
    label: 'Compliance Audit',
    fields: [
      { name: 'audit_name', label: 'Audit Name', type: 'text', placeholder: 'e.g., Annual SOC2 Audit' },
      { name: 'frameworks', label: 'Frameworks (comma-separated)', type: 'text', placeholder: 'e.g., SOC2, ISO27001, GDPR' },
      { name: 'audit_scope', label: 'Audit Scope', type: 'text', placeholder: 'e.g., full, partial, specific-controls' },
      { name: 'deadline', label: 'Deadline', type: 'text', placeholder: 'e.g., 2024-12-31' },
    ],
  },
  research_initiative: {
    label: 'Research Initiative',
    fields: [
      { name: 'research_name', label: 'Research Name', type: 'text', placeholder: 'e.g., AI-Powered Analytics R&D' },
      { name: 'research_area', label: 'Research Area', type: 'text', placeholder: 'e.g., machine learning, NLP, computer vision' },
      { name: 'objectives', label: 'Objectives (comma-separated)', type: 'text', placeholder: 'e.g., improve accuracy, reduce latency' },
      { name: 'budget', label: 'Budget ($)', type: 'number', placeholder: 'e.g., 500000' },
    ],
  },
  risk_assessment: {
    label: 'Risk Assessment',
    fields: [
      { name: 'assessment_name', label: 'Assessment Name', type: 'text', placeholder: 'e.g., Q4 Enterprise Risk Review' },
      { name: 'risk_categories', label: 'Risk Categories (comma-separated)', type: 'text', placeholder: 'e.g., operational, financial, security, compliance' },
      { name: 'scope', label: 'Scope', type: 'text', placeholder: 'e.g., enterprise-wide, department, project' },
      { name: 'risk_tolerance', label: 'Risk Tolerance', type: 'text', placeholder: 'e.g., low, medium, high' },
    ],
  },
  marketing_campaign: {
    label: 'Marketing Campaign',
    fields: [
      { name: 'campaign_name', label: 'Campaign Name', type: 'text', placeholder: 'e.g., Summer Product Launch' },
      { name: 'target_audience', label: 'Target Audience', type: 'text', placeholder: 'e.g., enterprise developers, IT leaders' },
      { name: 'channels', label: 'Channels (comma-separated)', type: 'text', placeholder: 'e.g., email, social, paid-ads, content' },
      { name: 'budget', label: 'Budget ($)', type: 'number', placeholder: 'e.g., 100000' },
    ],
  },
  sprint_planning: {
    label: 'Sprint Planning',
    fields: [
      { name: 'sprint_name', label: 'Sprint Name', type: 'text', placeholder: 'e.g., Sprint 23 - Auth Improvements' },
      { name: 'sprint_goals', label: 'Sprint Goals (comma-separated)', type: 'text', placeholder: 'e.g., SSO, password reset, MFA' },
      { name: 'team_capacity', label: 'Team Capacity (story points)', type: 'number', placeholder: 'e.g., 40' },
      { name: 'duration', label: 'Duration (days)', type: 'number', placeholder: 'e.g., 14' },
    ],
  },
  technology_migration: {
    label: 'Technology Migration',
    fields: [
      { name: 'migration_name', label: 'Migration Name', type: 'text', placeholder: 'e.g., Cloud Migration Phase 2' },
      { name: 'source_system', label: 'Source System', type: 'text', placeholder: 'e.g., on-premise datacenter' },
      { name: 'target_system', label: 'Target System', type: 'text', placeholder: 'e.g., AWS' },
      { name: 'components', label: 'Components (comma-separated)', type: 'text', placeholder: 'e.g., databases, APIs, storage' },
    ],
  },
  knowledge_transfer: {
    label: 'Knowledge Transfer',
    fields: [
      { name: 'transfer_name', label: 'Transfer Name', type: 'text', placeholder: 'e.g., Legacy System Documentation' },
      { name: 'knowledge_domain', label: 'Knowledge Domain', type: 'text', placeholder: 'e.g., payment processing, auth system' },
      { name: 'source_team', label: 'Source Team', type: 'text', placeholder: 'e.g., Core Platform' },
      { name: 'target_team', label: 'Target Team', type: 'text', placeholder: 'e.g., New Engineering Team' },
    ],
  },
  customer_churn_analysis: {
    label: 'Customer Churn Analysis',
    fields: [
      { name: 'analysis_name', label: 'Analysis Name', type: 'text', placeholder: 'e.g., Q3 Churn Deep Dive' },
      { name: 'customer_segments', label: 'Customer Segments (comma-separated)', type: 'text', placeholder: 'e.g., enterprise, mid-market, SMB' },
      { name: 'time_period', label: 'Time Period', type: 'text', placeholder: 'e.g., last 90 days' },
      { name: 'churn_threshold', label: 'Churn Threshold (%)', type: 'number', placeholder: 'e.g., 5' },
    ],
  },
  // Single-executive internal workflows
  operations_review: {
    label: 'Operations Review (COO)',
    fields: [
      { name: 'review_period', label: 'Review Period', type: 'text', placeholder: 'e.g., last_month, last_quarter' },
      { name: 'departments', label: 'Departments (comma-separated)', type: 'text', placeholder: 'e.g., engineering, sales, support' },
      { name: 'priority_areas', label: 'Priority Areas (comma-separated)', type: 'text', placeholder: 'e.g., efficiency, quality, throughput' },
    ],
  },
  tech_debt_review: {
    label: 'Tech Debt Review (CTO)',
    fields: [
      { name: 'codebase_areas', label: 'Codebase Areas (comma-separated)', type: 'text', placeholder: 'e.g., frontend, backend, infrastructure' },
      { name: 'debt_categories', label: 'Debt Categories (comma-separated)', type: 'text', placeholder: 'e.g., code_quality, dependencies, architecture' },
      { name: 'timeline', label: 'Remediation Timeline', type: 'text', placeholder: 'e.g., quarter, 6_months' },
    ],
  },
  financial_close: {
    label: 'Financial Close (CFO)',
    fields: [
      { name: 'close_period', label: 'Close Period', type: 'text', placeholder: 'e.g., Q4 2025, December 2025' },
      { name: 'revenue_streams', label: 'Revenue Streams (comma-separated)', type: 'text', placeholder: 'e.g., subscriptions, services, licenses' },
      { name: 'expense_categories', label: 'Expense Categories (comma-separated)', type: 'text', placeholder: 'e.g., payroll, infrastructure, marketing' },
    ],
  },
  code_quality: {
    label: 'Code Quality Review (CEngO)',
    fields: [
      { name: 'repositories', label: 'Repositories (comma-separated)', type: 'text', placeholder: 'e.g., api, frontend, services' },
      { name: 'coverage_target', label: 'Coverage Target (%)', type: 'number', placeholder: 'e.g., 80' },
      { name: 'priority_areas', label: 'Priority Areas (comma-separated)', type: 'text', placeholder: 'e.g., security, performance, maintainability' },
    ],
  },
  feature_prioritization: {
    label: 'Feature Prioritization (CPO)',
    fields: [
      { name: 'feature_sources', label: 'Feature Sources (comma-separated)', type: 'text', placeholder: 'e.g., feedback, sales, support' },
      { name: 'time_period', label: 'Time Period', type: 'text', placeholder: 'e.g., last_quarter' },
      { name: 'planning_horizon', label: 'Planning Horizon', type: 'text', placeholder: 'e.g., 6_months, 1_year' },
    ],
  },
  threat_monitoring: {
    label: 'Threat Monitoring (CSecO)',
    fields: [
      { name: 'scan_targets', label: 'Scan Targets (comma-separated)', type: 'text', placeholder: 'e.g., web_apps, apis, databases' },
      { name: 'severity_threshold', label: 'Severity Threshold', type: 'text', placeholder: 'e.g., low, medium, high, critical' },
      { name: 'industry_focus', label: 'Industry Focus', type: 'text', placeholder: 'e.g., fintech, healthcare, saas' },
    ],
  },
  data_pipeline_monitoring: {
    label: 'Data Pipeline Monitoring (CDO)',
    fields: [
      { name: 'pipelines', label: 'Pipelines (comma-separated)', type: 'text', placeholder: 'e.g., etl_main, analytics, reporting' },
      { name: 'monitoring_window', label: 'Monitoring Window', type: 'text', placeholder: 'e.g., 24h, 7d' },
      { name: 'optimization_targets', label: 'Optimization Targets (comma-separated)', type: 'text', placeholder: 'e.g., latency, cost, reliability' },
    ],
  },
  experiment_cycle: {
    label: 'Experiment Cycle (CRO)',
    fields: [
      { name: 'research_question', label: 'Research Question', type: 'text', placeholder: 'e.g., Does feature X improve conversion?' },
      { name: 'hypothesis', label: 'Hypothesis', type: 'text', placeholder: 'e.g., Adding X will increase conversion by 10%' },
      { name: 'experiment_type', label: 'Experiment Type', type: 'text', placeholder: 'e.g., ab_test, multivariate, cohort' },
      { name: 'duration', label: 'Duration', type: 'text', placeholder: 'e.g., 14_days, 30_days' },
    ],
  },
  customer_health_review: {
    label: 'Customer Health Review (CCO)',
    fields: [
      { name: 'customer_segments', label: 'Customer Segments (comma-separated)', type: 'text', placeholder: 'e.g., enterprise, mid-market, SMB' },
      { name: 'time_period', label: 'Time Period', type: 'text', placeholder: 'e.g., last_30_days' },
      { name: 'risk_threshold', label: 'Risk Threshold (0-1)', type: 'number', placeholder: 'e.g., 0.3' },
    ],
  },
  revenue_analysis: {
    label: 'Revenue Analysis (CRevO)',
    fields: [
      { name: 'analysis_period', label: 'Analysis Period', type: 'text', placeholder: 'e.g., last_quarter, last_year' },
      { name: 'revenue_streams', label: 'Revenue Streams (comma-separated)', type: 'text', placeholder: 'e.g., subscriptions, services, one-time' },
      { name: 'forecast_horizon', label: 'Forecast Horizon', type: 'text', placeholder: 'e.g., 12_months' },
    ],
  },
  risk_monitoring: {
    label: 'Risk Monitoring (CRiO)',
    fields: [
      { name: 'risk_categories', label: 'Risk Categories (comma-separated)', type: 'text', placeholder: 'e.g., operational, financial, compliance' },
      { name: 'update_period', label: 'Update Period', type: 'text', placeholder: 'e.g., monthly, weekly' },
      { name: 'audience', label: 'Report Audience', type: 'text', placeholder: 'e.g., board, executive, management' },
    ],
  },
  compliance_monitoring: {
    label: 'Compliance Monitoring (CComO)',
    fields: [
      { name: 'control_framework', label: 'Control Framework', type: 'text', placeholder: 'e.g., SOC2, ISO27001, GDPR' },
      { name: 'review_scope', label: 'Review Scope', type: 'text', placeholder: 'e.g., all_departments, engineering' },
      { name: 'report_period', label: 'Report Period', type: 'text', placeholder: 'e.g., Q4 2025' },
    ],
  },
  brand_health: {
    label: 'Brand Health (CMO)',
    fields: [
      { name: 'measurement_channels', label: 'Measurement Channels (comma-separated)', type: 'text', placeholder: 'e.g., survey, social, search' },
      { name: 'competitors', label: 'Competitors (comma-separated)', type: 'text', placeholder: 'e.g., CompA, CompB, CompC' },
      { name: 'time_period', label: 'Time Period', type: 'text', placeholder: 'e.g., last_quarter' },
    ],
  },
  infrastructure_health: {
    label: 'Infrastructure Health (CIO)',
    fields: [
      { name: 'systems', label: 'Systems (comma-separated)', type: 'text', placeholder: 'e.g., production, staging, databases' },
      { name: 'monitoring_window', label: 'Monitoring Window', type: 'text', placeholder: 'e.g., 24h, 7d' },
      { name: 'optimization_targets', label: 'Optimization Targets (comma-separated)', type: 'text', placeholder: 'e.g., cost, performance, reliability' },
    ],
  },
  knowledge_maintenance: {
    label: 'Knowledge Maintenance (CKO)',
    fields: [
      { name: 'knowledge_bases', label: 'Knowledge Bases (comma-separated)', type: 'text', placeholder: 'e.g., docs, wiki, runbooks' },
      { name: 'freshness_threshold', label: 'Freshness Threshold', type: 'text', placeholder: 'e.g., 90_days, 180_days' },
      { name: 'priority_areas', label: 'Priority Areas (comma-separated)', type: 'text', placeholder: 'e.g., onboarding, technical, processes' },
    ],
  },
  strategic_review: {
    label: 'Strategic Review (CSO)',
    fields: [
      { name: 'markets', label: 'Markets (comma-separated)', type: 'text', placeholder: 'e.g., north_america, europe, apac' },
      { name: 'competitors', label: 'Competitors (comma-separated)', type: 'text', placeholder: 'e.g., CompA, CompB' },
      { name: 'planning_horizon', label: 'Planning Horizon', type: 'text', placeholder: 'e.g., annual, 3_year' },
    ],
  },
}

export default function Workflows() {
  const [workflows, setWorkflows] = useState<Workflow[]>([])
  const [executions, setExecutions] = useState<WorkflowExecution[]>([])
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null)
  const [workflowDetails, setWorkflowDetails] = useState<Workflow | null>(null)
  const [showExecuteModal, setShowExecuteModal] = useState(false)
  const [executing, setExecuting] = useState(false)
  const [formParams, setFormParams] = useState<Record<string, string>>({})
  const [expandedExecution, setExpandedExecution] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchWorkflows()
    fetchHistory()
  }, [])

  useEffect(() => {
    if (selectedWorkflow) {
      fetchWorkflowDetails(selectedWorkflow)
    }
  }, [selectedWorkflow])

  const fetchWorkflows = async () => {
    try {
      const res = await fetch('/api/v1/workflows')
      if (res.ok) {
        const data = await res.json()
        setWorkflows(data.workflows || [])
      }
    } catch (e) {
      console.error('Failed to fetch workflows:', e)
    } finally {
      setLoading(false)
    }
  }

  const fetchWorkflowDetails = async (name: string) => {
    try {
      const res = await fetch(`/api/v1/workflows/${name}`)
      if (res.ok) {
        const data = await res.json()
        setWorkflowDetails(data)
      }
    } catch (e) {
      console.error('Failed to fetch workflow details:', e)
    }
  }

  const fetchHistory = async () => {
    try {
      const res = await fetch('/api/v1/workflows/history?limit=10')
      if (res.ok) {
        const data = await res.json()
        setExecutions(data.executions || [])
      }
    } catch (e) {
      console.error('Failed to fetch workflow history:', e)
    }
  }

  const handleExecute = async () => {
    if (!selectedWorkflow) return

    setExecuting(true)

    // Process params (convert comma-separated to arrays where needed)
    const params: Record<string, unknown> = { ...formParams }
    if (params.features && typeof params.features === 'string') {
      params.features = (params.features as string).split(',').map((f) => f.trim())
    }
    if (params.amount) {
      params.amount = parseFloat(params.amount as string)
    }

    try {
      const res = await fetch('/api/v1/workflows/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workflow_name: selectedWorkflow,
          params,
        }),
      })

      if (res.ok) {
        const result = await res.json()
        setExecutions((prev) => [result, ...prev])
        setExpandedExecution(result.workflow_id)
      } else {
        const error = await res.json()
        console.error('Workflow failed:', error)
      }
    } catch (e) {
      console.error('Failed to execute workflow:', e)
    } finally {
      setExecuting(false)
      setShowExecuteModal(false)
      setFormParams({})
    }
  }

  const openExecuteModal = (workflowName: string) => {
    setSelectedWorkflow(workflowName)
    setFormParams({})
    setShowExecuteModal(true)
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center">
        <Loader2 size={32} className="animate-spin text-csuite-accent" />
      </div>
    )
  }

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-csuite-text">Autonomous Workflows</h1>
          <p className="text-csuite-muted mt-1">
            Multi-executive coordinated workflows for complex business processes
          </p>
        </div>
        <button
          onClick={fetchHistory}
          className="flex items-center gap-2 px-4 py-2 text-csuite-muted hover:text-csuite-text transition-colors"
        >
          <RefreshCw size={20} />
          Refresh
        </button>
      </div>

      {/* Workflows Grid */}
      <section className="mb-8">
        <h2 className="text-lg font-semibold text-csuite-text mb-4">Available Workflows</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {workflows.map((workflow) => (
            <div
              key={workflow.name}
              className="bg-csuite-surface rounded-xl border border-csuite-border p-6 hover:border-csuite-accent/50 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-csuite-accent/10 rounded-lg">
                    <GitBranch size={24} className="text-csuite-accent" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-csuite-text">
                      {WORKFLOW_PARAMS[workflow.name]?.label || workflow.name}
                    </h3>
                    <p className="text-sm text-csuite-muted">{workflow.description}</p>
                  </div>
                </div>
                <button
                  onClick={() => openExecuteModal(workflow.name)}
                  className="flex items-center gap-2 px-4 py-2 bg-csuite-accent text-white rounded-lg hover:bg-indigo-600 transition-colors"
                >
                  <Play size={16} />
                  Run
                </button>
              </div>

              {/* Show workflow steps preview */}
              <button
                onClick={() => setSelectedWorkflow(selectedWorkflow === workflow.name ? null : workflow.name)}
                className="mt-4 flex items-center gap-2 text-sm text-csuite-muted hover:text-csuite-text"
              >
                {selectedWorkflow === workflow.name ? (
                  <ChevronDown size={16} />
                ) : (
                  <ChevronRight size={16} />
                )}
                View Steps
              </button>

              {selectedWorkflow === workflow.name && workflowDetails && (
                <div className="mt-4 space-y-2">
                  {workflowDetails.steps?.map((step, index) => (
                    <div
                      key={step.name}
                      className="flex items-center gap-3 text-sm bg-csuite-card rounded-lg p-3"
                    >
                      <span className="w-6 h-6 rounded-full bg-csuite-accent/20 text-csuite-accent flex items-center justify-center text-xs font-medium">
                        {index + 1}
                      </span>
                      <div className="flex-1">
                        <p className="text-csuite-text">{step.description}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <Users size={12} className="text-csuite-muted" />
                          <span className="text-xs text-csuite-muted">{step.executive}</span>
                          {!step.required && (
                            <span className="text-xs text-csuite-warning">(optional)</span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Execution History */}
      <section>
        <h2 className="text-lg font-semibold text-csuite-text mb-4">Execution History</h2>
        {executions.length > 0 ? (
          <div className="space-y-3">
            {executions.map((execution) => (
              <div
                key={execution.workflow_id}
                className="bg-csuite-surface rounded-xl border border-csuite-border overflow-hidden"
              >
                <div
                  className="p-4 cursor-pointer hover:bg-csuite-card/30 transition-colors"
                  onClick={() =>
                    setExpandedExecution(
                      expandedExecution === execution.workflow_id ? null : execution.workflow_id
                    )
                  }
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {execution.status === 'completed' ? (
                        <CheckCircle size={20} className="text-csuite-success" />
                      ) : execution.status === 'failed' ? (
                        <XCircle size={20} className="text-csuite-error" />
                      ) : (
                        <Clock size={20} className="text-csuite-muted" />
                      )}
                      <div>
                        <p className="text-csuite-text font-medium">
                          {WORKFLOW_PARAMS[execution.workflow_name]?.label || execution.workflow_name}
                        </p>
                        <p className="text-xs text-csuite-muted">
                          {new Date(execution.started_at).toLocaleString()}
                          {execution.duration_seconds && ` (${execution.duration_seconds.toFixed(1)}s)`}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={`px-2 py-1 rounded text-xs ${
                          execution.success
                            ? 'bg-csuite-success/10 text-csuite-success'
                            : 'bg-csuite-error/10 text-csuite-error'
                        }`}
                      >
                        {execution.status}
                      </span>
                      {expandedExecution === execution.workflow_id ? (
                        <ChevronDown size={20} className="text-csuite-muted" />
                      ) : (
                        <ChevronRight size={20} className="text-csuite-muted" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Expanded execution details */}
                {expandedExecution === execution.workflow_id && (
                  <div className="border-t border-csuite-border p-4 bg-csuite-card/30">
                    <h4 className="text-sm font-medium text-csuite-muted mb-3">Step Results</h4>
                    <div className="space-y-2">
                      {execution.steps.map((step) => (
                        <div
                          key={step.name}
                          className="flex items-start gap-3 bg-csuite-surface rounded-lg p-3"
                        >
                          {step.status === 'completed' ? (
                            <CheckCircle size={16} className="text-csuite-success mt-0.5" />
                          ) : step.status === 'failed' ? (
                            <XCircle size={16} className="text-csuite-error mt-0.5" />
                          ) : step.status === 'skipped' ? (
                            <Clock size={16} className="text-csuite-warning mt-0.5" />
                          ) : (
                            <Clock size={16} className="text-csuite-muted mt-0.5" />
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center justify-between">
                              <p className="text-sm text-csuite-text font-medium">{step.name}</p>
                              <span className="text-xs text-csuite-muted">{step.executive}</span>
                            </div>
                            {step.error && (
                              <p className="text-xs text-csuite-error mt-1">{String(step.error)}</p>
                            )}
                            {step.result !== undefined && step.result !== null && (
                              <p className="text-xs text-csuite-muted mt-1 truncate">
                                {typeof step.result === 'string'
                                  ? (step.result as string).slice(0, 100)
                                  : 'Result available'}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>

                    {execution.error && (
                      <div className="mt-4 p-3 bg-csuite-error/10 border border-csuite-error/30 rounded-lg">
                        <p className="text-sm text-csuite-error">{execution.error}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-csuite-surface rounded-xl border border-csuite-border p-8 text-center">
            <GitBranch size={48} className="mx-auto mb-2 text-csuite-muted opacity-50" />
            <p className="text-csuite-muted">No workflow executions yet</p>
            <p className="text-sm text-csuite-muted mt-1">
              Run a workflow to see results here
            </p>
          </div>
        )}
      </section>

      {/* Execute Workflow Modal */}
      {showExecuteModal && selectedWorkflow && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-csuite-surface rounded-xl border border-csuite-border p-6 w-full max-w-lg max-h-[80vh] overflow-y-auto">
            <h2 className="text-xl font-semibold text-csuite-text mb-4">
              Execute: {WORKFLOW_PARAMS[selectedWorkflow]?.label || selectedWorkflow}
            </h2>

            <div className="space-y-4">
              {WORKFLOW_PARAMS[selectedWorkflow]?.fields.map((field) => (
                <div key={field.name}>
                  <label className="block text-sm text-csuite-muted mb-1">{field.label}</label>
                  {field.type === 'select' ? (
                    <select
                      value={formParams[field.name] || ''}
                      onChange={(e) =>
                        setFormParams((prev) => ({ ...prev, [field.name]: e.target.value }))
                      }
                      className="w-full bg-csuite-card border border-csuite-border rounded-lg px-4 py-2 text-csuite-text"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="critical">Critical</option>
                    </select>
                  ) : (
                    <input
                      type={field.type}
                      placeholder={field.placeholder}
                      value={formParams[field.name] || ''}
                      onChange={(e) =>
                        setFormParams((prev) => ({ ...prev, [field.name]: e.target.value }))
                      }
                      className="w-full bg-csuite-card border border-csuite-border rounded-lg px-4 py-2 text-csuite-text"
                    />
                  )}
                </div>
              ))}
            </div>

            <div className="flex gap-3 justify-end mt-6">
              <button
                onClick={() => {
                  setShowExecuteModal(false)
                  setFormParams({})
                }}
                className="px-4 py-2 text-csuite-muted hover:text-csuite-text"
                disabled={executing}
              >
                Cancel
              </button>
              <button
                onClick={handleExecute}
                disabled={executing}
                className="px-4 py-2 bg-csuite-accent text-white rounded-lg hover:bg-indigo-600 disabled:opacity-50 flex items-center gap-2"
              >
                {executing && <Loader2 size={16} className="animate-spin" />}
                {executing ? 'Executing...' : 'Execute Workflow'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
