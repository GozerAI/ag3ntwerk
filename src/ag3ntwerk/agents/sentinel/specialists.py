"""
Sentinel (Sentinel) Information Governance Specialists.

Individual contributor specialists for specific information governance functions.
"""

import logging
from typing import Optional

from ag3ntwerk.core.base import Specialist, Task, TaskResult
from ag3ntwerk.llm.base import LLMProvider

logger = logging.getLogger(__name__)


class DataSteward(Specialist):
    """
    Data Steward - Expert data governance specialist.

    Responsible for:
    - Data quality management
    - Data classification
    - Metadata management
    - Data standards
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="DS",
            name="Data Steward",
            domain="Data Quality, Classification, Metadata",
            capabilities=[
                "data_quality_assessment",
                "data_classification",
                "metadata_management",
                "data_standards",
                "data_profiling",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if DataSteward can handle the task."""
        steward_types = [
            "data_quality_assessment",
            "data_classification",
            "metadata_management",
            "data_standards",
            "data_profiling",
            "data_quality_check",
        ]
        return task.task_type in steward_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "data_quality_assessment": self._handle_quality,
            "data_quality_check": self._handle_quality,
            "data_classification": self._handle_classification,
            "metadata_management": self._handle_metadata,
            "data_standards": self._handle_standards,
            "data_profiling": self._handle_profiling,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute data stewardship task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_quality(self, task: Task) -> TaskResult:
        """Handle data quality assessment."""
        context = task.context or {}

        prompt = f"""Assess data quality:

Data Asset: {task.description}
Dimensions: {context.get('dimensions', ['completeness', 'accuracy', 'consistency'])}
Sample: {context.get('sample', {})}

Quality Assessment:
1. Dimension scores
2. Issues identified
3. Root causes
4. Impact assessment
5. Remediation plan

Provide quality assessment.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_classification(self, task: Task) -> TaskResult:
        """Handle data classification."""
        context = task.context or {}

        prompt = f"""Classify data:

Data: {task.description}
Data Types: {context.get('data_types', [])}
Regulations: {context.get('regulations', [])}

Classification:
1. Sensitivity level
2. Classification rationale
3. Handling requirements
4. Access restrictions
5. Compliance requirements

Provide classification result.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_metadata(self, task: Task) -> TaskResult:
        """Handle metadata management."""
        context = task.context or {}

        prompt = f"""Manage metadata:

Asset: {task.description}
Current Metadata: {context.get('metadata', {})}
Standards: {context.get('standards', [])}

Metadata Management:
1. Required metadata fields
2. Current completeness
3. Quality issues
4. Enrichment recommendations
5. Governance status

Provide metadata assessment.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_standards(self, task: Task) -> TaskResult:
        """Handle data standards."""
        context = task.context or {}

        prompt = f"""Define data standards:

Domain: {task.description}
Scope: {context.get('scope', [])}
Requirements: {context.get('requirements', [])}

Standards Definition:
1. Naming conventions
2. Format specifications
3. Quality thresholds
4. Validation rules
5. Exception handling

Provide standards definition.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_profiling(self, task: Task) -> TaskResult:
        """Handle data profiling."""
        context = task.context or {}

        prompt = f"""Profile data:

Data Asset: {task.description}
Sample Size: {context.get('sample_size', 'full')}
Focus Areas: {context.get('focus', [])}

Profile Report:
1. Data statistics
2. Distribution analysis
3. Pattern detection
4. Anomaly identification
5. Quality indicators

Provide profiling report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a Data Steward, handle: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class CloudComplianceAnalyst(Specialist):
    """
    Cloud Compliance Analyst - Cloud infrastructure governance specialist.

    Responsible for:
    - Cloud provider compliance (AWS, Azure, GCP)
    - Infrastructure-as-code validation
    - Multi-cloud governance
    - Data residency compliance
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="CCA",
            name="Cloud Compliance Analyst",
            domain="Cloud Compliance, Infrastructure Governance, Data Residency",
            capabilities=[
                "cloud_compliance_audit",
                "iac_validation",
                "multi_cloud_governance",
                "data_residency_check",
                "cloud_security_posture",
                "cost_compliance",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if CloudComplianceAnalyst can handle the task."""
        cloud_types = [
            "cloud_compliance_audit",
            "cloud_compliance",
            "iac_validation",
            "infrastructure_validation",
            "multi_cloud_governance",
            "data_residency_check",
            "data_residency",
            "cloud_security_posture",
            "cloud_security",
            "cost_compliance",
        ]
        return task.task_type in cloud_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "cloud_compliance_audit": self._handle_compliance_audit,
            "cloud_compliance": self._handle_compliance_audit,
            "iac_validation": self._handle_iac_validation,
            "infrastructure_validation": self._handle_iac_validation,
            "multi_cloud_governance": self._handle_multi_cloud,
            "data_residency_check": self._handle_data_residency,
            "data_residency": self._handle_data_residency,
            "cloud_security_posture": self._handle_security_posture,
            "cloud_security": self._handle_security_posture,
            "cost_compliance": self._handle_cost_compliance,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute cloud compliance task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_compliance_audit(self, task: Task) -> TaskResult:
        """Handle cloud compliance audit."""
        context = task.context or {}

        prompt = f"""Audit cloud compliance:

Provider: {context.get('provider', 'multi-cloud')}
Scope: {task.description}
Frameworks: {context.get('frameworks', ['SOC2', 'ISO27001'])}

Compliance Audit:
1. Control mapping
2. Compliance status per framework
3. Gaps identified
4. Risk exposure
5. Remediation roadmap

Provide compliance audit report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_iac_validation(self, task: Task) -> TaskResult:
        """Handle infrastructure-as-code validation."""
        context = task.context or {}

        prompt = f"""Validate infrastructure-as-code:

Templates: {task.description}
Platform: {context.get('platform', 'terraform')}
Standards: {context.get('standards', [])}

IaC Validation:
1. Security misconfigurations
2. Best practice violations
3. Cost optimization opportunities
4. Drift detection
5. Remediation steps

Provide IaC validation report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_multi_cloud(self, task: Task) -> TaskResult:
        """Handle multi-cloud governance."""
        context = task.context or {}

        prompt = f"""Assess multi-cloud governance:

Providers: {context.get('providers', ['aws', 'azure', 'gcp'])}
Scope: {task.description}
Policies: {context.get('policies', [])}

Governance Assessment:
1. Policy consistency across providers
2. IAM alignment
3. Network segmentation
4. Data sovereignty compliance
5. Unified recommendations

Provide governance assessment.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_data_residency(self, task: Task) -> TaskResult:
        """Handle data residency compliance check."""
        context = task.context or {}

        prompt = f"""Check data residency compliance:

Data Assets: {task.description}
Jurisdictions: {context.get('jurisdictions', [])}
Regulations: {context.get('regulations', ['GDPR', 'CCPA'])}

Residency Check:
1. Data location mapping
2. Regulation applicability
3. Cross-border transfer assessment
4. Compliance gaps
5. Remediation actions

Provide data residency report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_security_posture(self, task: Task) -> TaskResult:
        """Handle cloud security posture assessment."""
        context = task.context or {}

        prompt = f"""Assess cloud security posture:

Environment: {task.description}
Provider: {context.get('provider', 'multi-cloud')}
Benchmarks: {context.get('benchmarks', ['CIS'])}

Security Posture:
1. Identity and access management
2. Network security
3. Data encryption
4. Logging and monitoring
5. Incident response readiness

Provide security posture assessment.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_cost_compliance(self, task: Task) -> TaskResult:
        """Handle cloud cost compliance."""
        context = task.context or {}

        prompt = f"""Audit cloud cost compliance:

Budget: {context.get('budget', 'unknown')}
Scope: {task.description}
Policies: {context.get('cost_policies', [])}

Cost Compliance:
1. Budget adherence
2. Tag compliance
3. Reserved capacity utilization
4. Waste identification
5. Optimization recommendations

Provide cost compliance report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a Cloud Compliance Analyst, assess: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class PrivacyGovernanceOfficer(Specialist):
    """
    Privacy Governance Officer - Data privacy and regulatory compliance specialist.

    Responsible for:
    - GDPR/CCPA compliance
    - Privacy impact assessments
    - Data subject rights management
    - Consent management
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="PGO",
            name="Privacy Governance Officer",
            domain="Data Privacy, Regulatory Compliance, Consent Management",
            capabilities=[
                "privacy_impact_assessment",
                "data_subject_rights",
                "consent_management",
                "privacy_compliance",
                "data_processor_audit",
                "breach_assessment",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if PrivacyGovernanceOfficer can handle the task."""
        privacy_types = [
            "privacy_impact_assessment",
            "privacy_assessment",
            "data_subject_rights",
            "data_subject_request",
            "consent_management",
            "consent_audit",
            "privacy_compliance",
            "privacy_audit",
            "data_processor_audit",
            "breach_assessment",
            "breach_notification",
        ]
        return task.task_type in privacy_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "privacy_impact_assessment": self._handle_pia,
            "privacy_assessment": self._handle_pia,
            "data_subject_rights": self._handle_dsr,
            "data_subject_request": self._handle_dsr,
            "consent_management": self._handle_consent,
            "consent_audit": self._handle_consent,
            "privacy_compliance": self._handle_compliance,
            "privacy_audit": self._handle_compliance,
            "data_processor_audit": self._handle_processor_audit,
            "breach_assessment": self._handle_breach,
            "breach_notification": self._handle_breach,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute privacy governance task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_pia(self, task: Task) -> TaskResult:
        """Handle privacy impact assessment."""
        context = task.context or {}

        prompt = f"""Conduct privacy impact assessment:

Project: {task.description}
Data Types: {context.get('data_types', [])}
Processing Activities: {context.get('activities', [])}

Privacy Impact Assessment:
1. Data flows mapped
2. Privacy risks identified
3. Lawful basis determination
4. Proportionality assessment
5. Mitigation measures

Provide PIA report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_dsr(self, task: Task) -> TaskResult:
        """Handle data subject rights request."""
        context = task.context or {}

        prompt = f"""Process data subject request:

Request Type: {context.get('request_type', 'access')}
Subject: {task.description}
Jurisdiction: {context.get('jurisdiction', 'EU')}

DSR Processing:
1. Request validation
2. Identity verification checklist
3. Data inventory search plan
4. Response template
5. Timeline and obligations

Provide DSR processing plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_consent(self, task: Task) -> TaskResult:
        """Handle consent management."""
        context = task.context or {}

        prompt = f"""Audit consent management:

System: {task.description}
Regulations: {context.get('regulations', ['GDPR'])}
Consent Types: {context.get('consent_types', [])}

Consent Audit:
1. Consent collection methods
2. Granularity assessment
3. Withdrawal mechanisms
4. Record-keeping status
5. Recommendations

Provide consent audit report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_compliance(self, task: Task) -> TaskResult:
        """Handle privacy compliance audit."""
        context = task.context or {}

        prompt = f"""Audit privacy compliance:

Scope: {task.description}
Frameworks: {context.get('frameworks', ['GDPR', 'CCPA'])}
Data Categories: {context.get('data_categories', [])}

Compliance Audit:
1. Data processing inventory
2. Legal basis per activity
3. Data protection measures
4. Cross-border transfers
5. Gap analysis and remediation

Provide privacy compliance report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_processor_audit(self, task: Task) -> TaskResult:
        """Handle third-party data processor audit."""
        context = task.context or {}

        prompt = f"""Audit data processor:

Processor: {task.description}
Agreement: {context.get('agreement_type', 'DPA')}
Categories: {context.get('data_categories', [])}

Processor Audit:
1. Agreement compliance
2. Security measures assessment
3. Sub-processor chain
4. Breach notification readiness
5. Recommendations

Provide processor audit report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_breach(self, task: Task) -> TaskResult:
        """Handle data breach assessment."""
        context = task.context or {}

        prompt = f"""Assess data breach:

Incident: {task.description}
Data Affected: {context.get('data_affected', [])}
Severity: {context.get('severity', 'unknown')}

Breach Assessment:
1. Scope determination
2. Risk to data subjects
3. Notification obligations
4. Timeline requirements
5. Remediation and prevention

Provide breach assessment.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a Privacy Governance Officer, assess: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class SecurityAnalyst(Specialist):
    """
    Security Analyst - Expert security analysis specialist.

    Responsible for:
    - Vulnerability analysis
    - Threat assessment
    - Security reviews
    - Risk analysis
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="SEA",
            name="Security Analyst",
            domain="Security Analysis, Vulnerability, Threat Assessment",
            capabilities=[
                "vulnerability_analysis",
                "threat_assessment",
                "security_review",
                "risk_analysis",
                "compliance_assessment",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if SecurityAnalyst can handle the task."""
        security_types = [
            "vulnerability_analysis",
            "vulnerability_check",
            "threat_assessment",
            "threat_analysis",
            "security_review",
            "security_scan",
            "risk_analysis",
            "risk_assessment",
            "compliance_assessment",
            "compliance_check",
        ]
        return task.task_type in security_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "vulnerability_analysis": self._handle_vulnerability,
            "vulnerability_check": self._handle_vulnerability,
            "threat_assessment": self._handle_threat,
            "threat_analysis": self._handle_threat,
            "security_review": self._handle_security_review,
            "security_scan": self._handle_security_review,
            "risk_analysis": self._handle_risk,
            "risk_assessment": self._handle_risk,
            "compliance_assessment": self._handle_compliance,
            "compliance_check": self._handle_compliance,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute security analysis task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_vulnerability(self, task: Task) -> TaskResult:
        """Handle vulnerability analysis."""
        context = task.context or {}
        target = context.get("target", "unknown")

        prompt = f"""Analyze vulnerabilities:

Target: {target}
Description: {task.description}
Scope: {context.get('scope', 'full')}

Vulnerability Analysis:
1. Vulnerability inventory
2. Severity assessment
3. Exploitability analysis
4. Impact assessment
5. Remediation priority

Provide vulnerability analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_threat(self, task: Task) -> TaskResult:
        """Handle threat assessment."""
        context = task.context or {}

        prompt = f"""Assess threats:

Subject: {task.description}
Assets: {context.get('assets', [])}
Environment: {context.get('environment', 'standard')}

Threat Assessment:
1. Threat actors
2. Attack vectors
3. Likelihood analysis
4. Impact analysis
5. Mitigation recommendations

Provide threat assessment.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_security_review(self, task: Task) -> TaskResult:
        """Handle security review."""
        context = task.context or {}

        prompt = f"""Perform security review:

Target: {task.description}
Scope: {context.get('scope', 'comprehensive')}
Standards: {context.get('standards', ['OWASP'])}

Security Review:
1. Security posture
2. Findings by severity
3. Control gaps
4. Compliance status
5. Recommendations

Provide security review.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_risk(self, task: Task) -> TaskResult:
        """Handle risk analysis."""
        context = task.context or {}

        prompt = f"""Analyze risk:

Subject: {task.description}
Assets: {context.get('assets', [])}
Threats: {context.get('threats', [])}

Risk Analysis:
1. Risk identification
2. Likelihood x Impact
3. Risk score
4. Risk ranking
5. Mitigation options

Provide risk analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_compliance(self, task: Task) -> TaskResult:
        """Handle compliance assessment."""
        context = task.context or {}

        prompt = f"""Assess compliance:

Framework: {context.get('framework', 'general')}
Scope: {task.description}
Controls: {context.get('controls', [])}

Compliance Assessment:
1. Control status
2. Gaps identified
3. Evidence review
4. Risk exposure
5. Remediation plan

Provide compliance assessment.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a Security Analyst, analyze: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class KnowledgeSpecialist(Specialist):
    """
    Knowledge Specialist - Expert knowledge management specialist.

    Responsible for:
    - Knowledge creation
    - Content curation
    - Taxonomy management
    - Search optimization
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="KS",
            name="Knowledge Specialist",
            domain="Knowledge Creation, Curation, Taxonomy",
            capabilities=[
                "knowledge_creation",
                "content_curation",
                "taxonomy_management",
                "search_optimization",
                "knowledge_mapping",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if KnowledgeSpecialist can handle the task."""
        knowledge_types = [
            "knowledge_creation",
            "content_curation",
            "taxonomy_management",
            "search_optimization",
            "knowledge_mapping",
            "knowledge_retrieval",
            "knowledge_curation",
        ]
        return task.task_type in knowledge_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "knowledge_creation": self._handle_creation,
            "content_curation": self._handle_curation,
            "knowledge_curation": self._handle_curation,
            "taxonomy_management": self._handle_taxonomy,
            "search_optimization": self._handle_search,
            "knowledge_mapping": self._handle_mapping,
            "knowledge_retrieval": self._handle_retrieval,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute knowledge specialist task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_creation(self, task: Task) -> TaskResult:
        """Handle knowledge creation."""
        context = task.context or {}

        prompt = f"""Create knowledge content:

Topic: {task.description}
Format: {context.get('format', 'article')}
Audience: {context.get('audience', 'general')}

Content Creation:
1. Structured content
2. Key points
3. Examples
4. References
5. Related topics

Provide knowledge content.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_curation(self, task: Task) -> TaskResult:
        """Handle content curation."""
        context = task.context or {}

        prompt = f"""Curate content:

Content: {task.description}
Quality Standards: {context.get('standards', [])}
Purpose: {context.get('purpose', 'general')}

Curation Report:
1. Quality assessment
2. Accuracy check
3. Relevance score
4. Update needs
5. Recommendations

Provide curation report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_taxonomy(self, task: Task) -> TaskResult:
        """Handle taxonomy management."""
        context = task.context or {}

        prompt = f"""Manage taxonomy:

Domain: {task.description}
Current Structure: {context.get('structure', {})}
Requirements: {context.get('requirements', [])}

Taxonomy Analysis:
1. Category structure
2. Relationships
3. Gap analysis
4. Consolidation opportunities
5. Recommendations

Provide taxonomy analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_search(self, task: Task) -> TaskResult:
        """Handle search optimization."""
        context = task.context or {}

        prompt = f"""Optimize search:

Content: {task.description}
Search Patterns: {context.get('patterns', [])}
User Feedback: {context.get('feedback', [])}

Search Optimization:
1. Keyword analysis
2. Metadata enhancement
3. Synonym mapping
4. Relevance tuning
5. Performance metrics

Provide optimization recommendations.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_mapping(self, task: Task) -> TaskResult:
        """Handle knowledge mapping."""
        context = task.context or {}

        prompt = f"""Map knowledge:

Domain: {task.description}
Scope: {context.get('scope', 'full')}
Focus: {context.get('focus', [])}

Knowledge Map:
1. Knowledge areas
2. Relationships
3. Experts mapping
4. Gap analysis
5. Recommendations

Provide knowledge map.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_retrieval(self, task: Task) -> TaskResult:
        """Handle knowledge retrieval."""
        context = task.context or {}

        prompt = f"""Retrieve knowledge:

Query: {task.description}
Filters: {context.get('filters', {})}
Context: {context.get('context', {})}

Retrieval Results:
1. Relevant content
2. Key insights
3. Related topics
4. Expert references
5. Additional resources

Provide retrieval results.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a Knowledge Specialist, handle: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))


class SystemsAnalyst(Specialist):
    """
    Systems Analyst - Expert IT systems specialist.

    Responsible for:
    - System analysis
    - Integration design
    - Performance analysis
    - Capacity planning
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        super().__init__(
            code="SYA",
            name="Systems Analyst",
            domain="Systems Analysis, Integration, Performance",
            capabilities=[
                "system_analysis",
                "integration_design",
                "performance_analysis",
                "capacity_planning",
                "architecture_review",
            ],
            llm_provider=llm_provider,
        )

    def can_handle(self, task: Task) -> bool:
        """Check if SystemsAnalyst can handle the task."""
        system_types = [
            "system_analysis",
            "system_inventory",
            "integration_design",
            "integration_management",
            "performance_analysis",
            "capacity_planning",
            "architecture_review",
            "health_monitoring",
        ]
        return task.task_type in system_types

    def _get_handler(self, task_type: str):
        """Get handler for task type."""
        handlers = {
            "system_analysis": self._handle_analysis,
            "system_inventory": self._handle_inventory,
            "integration_design": self._handle_integration,
            "integration_management": self._handle_integration,
            "performance_analysis": self._handle_performance,
            "capacity_planning": self._handle_capacity,
            "architecture_review": self._handle_architecture,
            "health_monitoring": self._handle_health,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute systems analysis task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)
        return await self._default_handler(task)

    async def _handle_analysis(self, task: Task) -> TaskResult:
        """Handle system analysis."""
        context = task.context or {}

        prompt = f"""Analyze system:

System: {task.description}
Scope: {context.get('scope', 'full')}
Focus: {context.get('focus', [])}

System Analysis:
1. System overview
2. Component analysis
3. Dependency mapping
4. Issues identified
5. Recommendations

Provide system analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_inventory(self, task: Task) -> TaskResult:
        """Handle system inventory."""
        context = task.context or {}

        prompt = f"""Inventory systems:

Scope: {task.description}
Categories: {context.get('categories', [])}
Attributes: {context.get('attributes', [])}

Inventory Report:
1. System list
2. Classification
3. Status summary
4. Gaps identified
5. Recommendations

Provide inventory report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_integration(self, task: Task) -> TaskResult:
        """Handle integration design."""
        context = task.context or {}

        prompt = f"""Design integration:

Integration: {task.description}
Systems: {context.get('systems', [])}
Requirements: {context.get('requirements', [])}

Integration Design:
1. Integration pattern
2. Data mapping
3. Error handling
4. Security considerations
5. Monitoring approach

Provide integration design.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_performance(self, task: Task) -> TaskResult:
        """Handle performance analysis."""
        context = task.context or {}

        prompt = f"""Analyze performance:

System: {task.description}
Metrics: {context.get('metrics', {})}
SLAs: {context.get('slas', {})}

Performance Analysis:
1. Current performance
2. Bottlenecks
3. Trend analysis
4. Optimization opportunities
5. Recommendations

Provide performance analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_capacity(self, task: Task) -> TaskResult:
        """Handle capacity planning."""
        context = task.context or {}

        prompt = f"""Plan capacity:

System: {task.description}
Current Usage: {context.get('usage', {})}
Growth Projections: {context.get('projections', {})}

Capacity Plan:
1. Current capacity
2. Utilization analysis
3. Growth forecast
4. Scaling recommendations
5. Cost implications

Provide capacity plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_architecture(self, task: Task) -> TaskResult:
        """Handle architecture review."""
        context = task.context or {}

        prompt = f"""Review architecture:

System: {task.description}
Current State: {context.get('current', {})}
Requirements: {context.get('requirements', [])}

Architecture Review:
1. Current architecture
2. Strengths
3. Weaknesses
4. Improvement areas
5. Recommendations

Provide architecture review.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_health(self, task: Task) -> TaskResult:
        """Handle health monitoring."""
        context = task.context or {}

        prompt = f"""Monitor health:

Systems: {task.description}
Metrics: {context.get('metrics', {})}
Thresholds: {context.get('thresholds', {})}

Health Report:
1. Overall status
2. Component health
3. Alerts
4. Trends
5. Recommendations

Provide health report.
"""
        return await self._execute_with_llm(task, prompt)

    async def _default_handler(self, task: Task) -> TaskResult:
        """Default handler."""
        prompt = f"As a Systems Analyst, analyze: {task.description}"
        return await self._execute_with_llm(task, prompt)

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute with LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(task_id=task.id, success=True, output=response)
        except Exception as e:
            return TaskResult(task_id=task.id, success=False, error=str(e))
