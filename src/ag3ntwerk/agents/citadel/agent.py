"""
Citadel (Citadel) Agent - Citadel.

Codename: Citadel
Core function: Security operations, threat management, and Sentinel platform bridge.

The Citadel bridges ag3ntwerk with the Sentinel security platform, handling:
- Threat detection and response
- Vulnerability management
- Security incident response
- Compliance and policy management
- Access reviews and identity governance
- Security automation and orchestration
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from ag3ntwerk.core.base import Manager, Task, TaskResult, TaskStatus
from ag3ntwerk.llm.base import LLMProvider

from ag3ntwerk.agents.citadel.models import (
    SECURITY_CAPABILITIES,
    Threat,
    ThreatSeverity,
    ThreatStatus,
    Vulnerability,
    VulnerabilityStatus,
    SecurityScan,
    ScanType,
    ScanStatus,
    SecurityIncident,
    IncidentSeverity,
    IncidentStatus,
    SecurityPolicy,
    PolicyType,
    ComplianceControl,
    ComplianceStatus,
    AccessReview,
    SentinelAgentMapping,
    SecurityMetrics,
)

if TYPE_CHECKING:
    from ag3ntwerk.agents.citadel.bridge import SentinelBridge

logger = logging.getLogger(__name__)


# Sentinel agent mappings
SENTINEL_AGENT_MAPPINGS = {
    "threat_detection": SentinelAgentMapping(
        task_type="threat_detection",
        sentinel_agent="guardian",
        fallback_agent="observer",
    ),
    "threat_analysis": SentinelAgentMapping(
        task_type="threat_analysis",
        sentinel_agent="guardian",
        fallback_agent="strategy",
    ),
    "vulnerability_scanning": SentinelAgentMapping(
        task_type="vulnerability_scanning",
        sentinel_agent="discovery",
        fallback_agent="guardian",
    ),
    "security_monitoring": SentinelAgentMapping(
        task_type="security_monitoring",
        sentinel_agent="observer",
        fallback_agent="guardian",
    ),
    "incident_response": SentinelAgentMapping(
        task_type="incident_response",
        sentinel_agent="healer",
        fallback_agent="guardian",
    ),
    "policy_enforcement": SentinelAgentMapping(
        task_type="policy_enforcement",
        sentinel_agent="policy",
        fallback_agent="guardian",
    ),
    "security_automation": SentinelAgentMapping(
        task_type="security_automation",
        sentinel_agent="strategy",
        fallback_agent="planner",
    ),
}


class Citadel(Manager):
    """
    Citadel (Citadel) - Citadel.

    The Citadel is the security agent in ag3ntwerk, responsible for:
    - Bridging ag3ntwerk with Sentinel security platform
    - Overseeing all security operations
    - Managing threat detection and response
    - Coordinating vulnerability management
    - Ensuring compliance and governance
    - Managing security policies

    The Citadel codename reflects its role as the fortress protecting
    the enterprise from security threats.
    """

    def __init__(self, llm_provider: Optional["LLMProvider"] = None):
        """Initialize the Citadel agent."""
        super().__init__(
            code="Citadel",
            name="Citadel",
            domain="Security Operations, Threat Management, Compliance, AppSec",
            llm_provider=llm_provider,
        )

        self.codename = "Citadel"
        self.capabilities = SECURITY_CAPABILITIES

        # State
        self.threats: Dict[str, Threat] = {}
        self.vulnerabilities: Dict[str, Vulnerability] = {}
        self.scans: Dict[str, SecurityScan] = {}
        self.incidents: Dict[str, SecurityIncident] = {}
        self.policies: Dict[str, SecurityPolicy] = {}
        self.controls: Dict[str, ComplianceControl] = {}
        self.access_reviews: Dict[str, AccessReview] = {}

        # Sentinel integration
        self._sentinel_engine = None
        self._sentinel_bridge: Optional["SentinelBridge"] = None
        self._sentinel_connected = False

        # Initialize managers and specialists
        self._init_managers()

    def _init_managers(self) -> None:
        """Initialize security managers and specialists."""
        from ag3ntwerk.agents.citadel.managers import (
            ThreatManager,
            VulnerabilityManager,
            ComplianceManager,
            SOCManager,
        )
        from ag3ntwerk.agents.citadel.specialists import (
            ThreatHunter,
            VulnerabilityAnalyst,
            IncidentResponder,
            ComplianceAnalyst,
            SecurityEngineer,
            AppSecEngineer,
        )

        # Create managers
        tm = ThreatManager(llm_provider=self.llm_provider)
        vm = VulnerabilityManager(llm_provider=self.llm_provider)
        cm = ComplianceManager(llm_provider=self.llm_provider)
        socm = SOCManager(llm_provider=self.llm_provider)

        # Create specialists
        th = ThreatHunter(llm_provider=self.llm_provider)
        va = VulnerabilityAnalyst(llm_provider=self.llm_provider)
        ir = IncidentResponder(llm_provider=self.llm_provider)
        ca = ComplianceAnalyst(llm_provider=self.llm_provider)
        se = SecurityEngineer(llm_provider=self.llm_provider)
        ase = AppSecEngineer(llm_provider=self.llm_provider)

        # Register specialists under managers
        tm.register_subordinate(th)
        vm.register_subordinate(va)
        vm.register_subordinate(ase)
        socm.register_subordinate(ir)
        socm.register_subordinate(se)
        cm.register_subordinate(ca)

        # Register managers
        self.register_subordinate(tm)
        self.register_subordinate(vm)
        self.register_subordinate(cm)
        self.register_subordinate(socm)

    async def connect_sentinel(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
    ) -> bool:
        """
        Connect to the Sentinel security platform via SentinelBridge.

        Args:
            config: Sentinel configuration including connection details
            config_path: Optional path to Sentinel configuration file

        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Use the SentinelBridge for clean integration
            from ag3ntwerk.agents.citadel.bridge import SentinelBridge

            self._sentinel_bridge = SentinelBridge(config)
            success = await self._sentinel_bridge.connect(config_path)

            if success:
                self._sentinel_connected = True
                logger.info("Successfully connected to Sentinel platform via bridge")
                return True
            else:
                logger.warning("Failed to connect to Sentinel via bridge")
                return False

        except ImportError as e:
            logger.warning(f"Sentinel platform not available - running in standalone mode: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Sentinel: {e}")
            return False

    async def connect_sentinel_engine(self, config: Dict[str, Any]) -> bool:
        """
        Connect directly to Sentinel engine (legacy method).

        For most use cases, prefer connect_sentinel() which uses the SentinelBridge.

        Args:
            config: Sentinel configuration

        Returns:
            True if connection successful
        """
        try:
            from sentinel.core.engine import SentinelEngine

            self._sentinel_engine = SentinelEngine(config)
            await self._sentinel_engine.start()
            self._sentinel_connected = True
            logger.info("Successfully connected to Sentinel engine directly")
            return True
        except ImportError:
            logger.warning("Sentinel engine not available")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Sentinel engine: {e}")
            return False

    async def disconnect_sentinel(self) -> bool:
        """Disconnect from Sentinel platform."""
        try:
            # Disconnect bridge if connected
            if self._sentinel_bridge:
                await self._sentinel_bridge.disconnect()
                self._sentinel_bridge = None

            # Disconnect engine if connected
            if self._sentinel_engine:
                await self._sentinel_engine.stop()
                self._sentinel_engine = None

            self._sentinel_connected = False
            logger.info("Disconnected from Sentinel platform")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting from Sentinel: {e}")
            return False

    @property
    def sentinel_connected(self) -> bool:
        """Check if Sentinel is connected."""
        return self._sentinel_connected

    def can_handle(self, task: Task) -> bool:
        """Check if Citadel can handle the task."""
        security_types = [
            "threat_detection",
            "threat_analysis",
            "threat_hunting",
            "threat_mitigation",
            "vulnerability_scan",
            "vulnerability_assessment",
            "vulnerability_remediation",
            "security_scan",
            "penetration_test",
            "incident_response",
            "incident_investigation",
            "forensics",
            "compliance_assessment",
            "compliance_audit",
            "policy_management",
            "access_review",
            "security_monitoring",
            "siem_operations",
            "code_review",
            "sast_scan",
            "dast_scan",
            "dependency_scan",
            "security_automation",
        ]
        return task.task_type in security_types or any(
            cap in task.description.lower()
            for cap in ["security", "threat", "vulnerability", "compliance"]
        )

    def _get_handler(self, task_type: str):
        """Get the handler method for a task type."""
        handlers = {
            # Threat management
            "threat_detection": self._handle_threat_detection,
            "threat_analysis": self._handle_threat_analysis,
            "threat_hunting": self._handle_threat_hunting,
            "threat_mitigation": self._handle_threat_mitigation,
            # Vulnerability management
            "vulnerability_scan": self._handle_vulnerability_scan,
            "vulnerability_assessment": self._handle_vulnerability_assessment,
            "vulnerability_remediation": self._handle_vulnerability_remediation,
            "security_scan": self._handle_security_scan,
            "penetration_test": self._handle_penetration_test,
            # Incident response
            "incident_response": self._handle_incident_response,
            "incident_investigation": self._handle_incident_investigation,
            "forensics": self._handle_forensics,
            # Compliance
            "compliance_assessment": self._handle_compliance_assessment,
            "compliance_audit": self._handle_compliance_audit,
            "policy_management": self._handle_policy_management,
            # Access
            "access_review": self._handle_access_review,
            # Operations
            "security_monitoring": self._handle_security_monitoring,
            "siem_operations": self._handle_siem_operations,
            "security_automation": self._handle_security_automation,
            # AppSec
            "code_review": self._handle_code_review,
            "sast_scan": self._handle_sast_scan,
            "dast_scan": self._handle_dast_scan,
            "dependency_scan": self._handle_dependency_scan,
        }
        return handlers.get(task_type)

    async def execute(self, task: Task) -> TaskResult:
        """Execute a security task."""
        handler = self._get_handler(task.task_type)
        if handler:
            return await handler(task)

        # Check if we can route to Sentinel
        if self._sentinel_connected and task.task_type in SENTINEL_AGENT_MAPPINGS:
            return await self._route_to_sentinel(task)

        # Try to delegate to appropriate manager
        return await self._route_to_manager(task)

    async def _route_to_sentinel(self, task: Task) -> TaskResult:
        """Route task to Sentinel via bridge or directly to engine."""
        # Prefer the bridge if available
        if self._sentinel_bridge and self._sentinel_bridge.is_connected:
            return await self._sentinel_bridge.execute_task(task)

        # Fall back to direct engine access
        mapping = SENTINEL_AGENT_MAPPINGS.get(task.task_type)
        if not mapping:
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"No Sentinel mapping for task type: {task.task_type}",
            )

        if not self._sentinel_engine:
            return TaskResult(
                task_id=task.id,
                success=False,
                error="Sentinel not connected (neither bridge nor engine)",
            )

        try:
            # Get Sentinel agent from engine
            agent = self._sentinel_engine.get_agent(mapping.sentinel_agent)
            if not agent:
                # Try fallback
                if mapping.fallback_agent:
                    agent = self._sentinel_engine.get_agent(mapping.fallback_agent)

            if not agent:
                return TaskResult(
                    task_id=task.id,
                    success=False,
                    error=f"No Sentinel agent available for: {task.task_type}",
                )

            # Convert task and execute
            sentinel_task = {
                "id": task.id,
                "type": task.task_type,
                "description": task.description,
                "context": task.context,
                "priority": task.priority,
            }

            result = await agent.execute_task(sentinel_task)

            return TaskResult(
                task_id=task.id,
                success=result.get("success", False),
                output=result.get("output"),
                error=result.get("error"),
                metadata={"sentinel_agent": mapping.sentinel_agent},
            )
        except Exception as e:
            logger.error(f"Sentinel execution failed: {e}")
            return TaskResult(
                task_id=task.id,
                success=False,
                error=f"Sentinel execution failed: {str(e)}",
            )

    async def _route_to_manager(self, task: Task) -> TaskResult:
        """Route task to appropriate manager."""
        for manager in self.subordinates:
            if manager.can_handle(task):
                return await manager.execute(task)

        return TaskResult(
            task_id=task.id,
            success=False,
            error=f"No handler for task type: {task.task_type}",
        )

    # Threat Management Handlers
    async def _handle_threat_detection(self, task: Task) -> TaskResult:
        """Handle threat detection task."""
        context = task.context or {}

        prompt = f"""Analyze the following for potential threats:

Target: {context.get('target', 'Not specified')}
Data Sources: {context.get('data_sources', [])}
Indicators: {context.get('indicators', [])}
Timeframe: {context.get('timeframe', 'Last 24 hours')}

Detection Requirements:
1. Identify any indicators of compromise (IOCs)
2. Correlate with known threat intelligence
3. Assess threat severity and urgency
4. Recommend immediate actions

Provide structured threat detection analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_threat_analysis(self, task: Task) -> TaskResult:
        """Handle threat analysis task."""
        context = task.context or {}
        threat_id = context.get("threat_id")

        threat = self.threats.get(threat_id) if threat_id else None
        threat_info = (
            f"Threat: {threat.name} - {threat.description}" if threat else "No specific threat"
        )

        prompt = f"""Analyze the following threat:

{threat_info}
Attack Vector: {context.get('attack_vector', 'Unknown')}
Affected Systems: {context.get('affected_systems', [])}
Indicators: {context.get('indicators', [])}

Analysis Requirements:
1. Determine threat actor tactics, techniques, and procedures (TTPs)
2. Map to MITRE ATT&CK framework
3. Assess potential impact and blast radius
4. Identify attack chain and kill chain stage
5. Recommend containment and mitigation strategies

Provide detailed threat analysis.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_threat_hunting(self, task: Task) -> TaskResult:
        """Handle proactive threat hunting task."""
        context = task.context or {}

        prompt = f"""Conduct proactive threat hunting:

Hunt Hypothesis: {context.get('hypothesis', 'General APT activity')}
Target Environment: {context.get('environment', 'Enterprise network')}
Data Sources: {context.get('data_sources', [])}
Known Threats: {context.get('known_threats', [])}

Hunting Requirements:
1. Define hunting queries and detection logic
2. Identify anomalous behaviors and patterns
3. Correlate across multiple data sources
4. Document findings and false positives
5. Create detection rules for identified threats

Provide threat hunting plan and findings.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_threat_mitigation(self, task: Task) -> TaskResult:
        """Handle threat mitigation task."""
        context = task.context or {}
        threat_id = context.get("threat_id")
        threat = self.threats.get(threat_id) if threat_id else None

        prompt = f"""Develop threat mitigation strategy:

Threat: {threat.name if threat else context.get('threat_name', 'Unknown')}
Severity: {threat.severity.value if threat else context.get('severity', 'medium')}
Affected Systems: {context.get('affected_systems', [])}
Current Status: {threat.status.value if threat else 'unknown'}

Mitigation Requirements:
1. Immediate containment actions
2. Eradication steps
3. Recovery procedures
4. Prevention measures
5. Validation and monitoring

Provide detailed mitigation plan with priorities.
"""
        result = await self._execute_with_llm(task, prompt)

        # Update threat status if successful
        if result.success and threat:
            try:
                threat.status = ThreatStatus.MITIGATED
                threat.notes.append(
                    f"Mitigation initiated: {datetime.now(timezone.utc).isoformat()}"
                )
            except Exception as e:
                logger.warning(f"Failed to update threat status: {e}")

        return result

    # Vulnerability Management Handlers
    async def _handle_vulnerability_scan(self, task: Task) -> TaskResult:
        """Handle vulnerability scanning task."""
        context = task.context or {}

        scan = SecurityScan(
            name=context.get("name", "Vulnerability Scan"),
            scan_type=ScanType.VULNERABILITY,
            target=context.get("target", ""),
            scope=context.get("scope", []),
            status=ScanStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self.scans[scan.id] = scan

        prompt = f"""Plan and execute vulnerability scan:

Target: {scan.target}
Scope: {scan.scope}
Scan Type: {context.get('scan_type', 'comprehensive')}
Credentials: {'Authenticated' if context.get('authenticated') else 'Unauthenticated'}

Scanning Requirements:
1. Define scan configuration and scope
2. Identify potential vulnerabilities
3. Categorize by severity (CVSS)
4. Map to CVE identifiers where applicable
5. Prioritize findings by risk

Provide scan plan and expected findings.
"""
        result = await self._execute_with_llm(task, prompt)

        # Update scan status with error handling
        try:
            scan.status = ScanStatus.COMPLETED if result.success else ScanStatus.FAILED
            scan.completed_at = datetime.now(timezone.utc)
        except Exception as e:
            logger.warning(f"Failed to update scan status: {e}")

        return result

    async def _handle_vulnerability_assessment(self, task: Task) -> TaskResult:
        """Handle vulnerability assessment task."""
        context = task.context or {}

        prompt = f"""Conduct vulnerability assessment:

Scope: {context.get('scope', 'Full infrastructure')}
Assets: {context.get('assets', [])}
Previous Findings: {context.get('previous_findings', 'None')}

Assessment Requirements:
1. Review existing vulnerability scan results
2. Validate and verify findings
3. Assess exploitability and impact
4. Determine risk ratings
5. Prioritize remediation efforts

Provide comprehensive vulnerability assessment.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_vulnerability_remediation(self, task: Task) -> TaskResult:
        """Handle vulnerability remediation task."""
        context = task.context or {}
        vuln_id = context.get("vulnerability_id")
        vuln = self.vulnerabilities.get(vuln_id) if vuln_id else None

        prompt = f"""Plan vulnerability remediation:

Vulnerability: {vuln.title if vuln else context.get('vulnerability_title', 'Unknown')}
CVE: {vuln.cve_id if vuln else context.get('cve_id', 'N/A')}
CVSS Score: {vuln.cvss_score if vuln else context.get('cvss_score', 'N/A')}
Affected Asset: {vuln.affected_asset if vuln else context.get('asset', 'Unknown')}

Remediation Requirements:
1. Analyze remediation options
2. Assess impact of remediation
3. Plan testing and validation
4. Define rollback procedures
5. Schedule implementation

Provide remediation plan with timeline.
"""
        result = await self._execute_with_llm(task, prompt)

        if result.success and vuln:
            vuln.status = VulnerabilityStatus.IN_PROGRESS

        return result

    async def _handle_security_scan(self, task: Task) -> TaskResult:
        """Handle general security scan task."""
        context = task.context or {}

        scan = SecurityScan(
            name=context.get("name", "Security Scan"),
            scan_type=ScanType(context.get("scan_type", "configuration")),
            target=context.get("target", ""),
            scope=context.get("scope", []),
            status=ScanStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self.scans[scan.id] = scan

        prompt = f"""Conduct security scan:

Scan Type: {scan.scan_type.value}
Target: {scan.target}
Scope: {scan.scope}
Configuration: {context.get('configuration', {})}

Scan Requirements:
1. Define scan parameters
2. Execute security checks
3. Identify misconfigurations
4. Assess security posture
5. Generate actionable findings

Provide scan results and recommendations.
"""
        result = await self._execute_with_llm(task, prompt)

        scan.status = ScanStatus.COMPLETED if result.success else ScanStatus.FAILED
        scan.completed_at = datetime.now(timezone.utc)

        return result

    async def _handle_penetration_test(self, task: Task) -> TaskResult:
        """Handle penetration testing task."""
        context = task.context or {}

        prompt = f"""Plan penetration test:

Scope: {context.get('scope', [])}
Target Systems: {context.get('targets', [])}
Test Type: {context.get('test_type', 'black_box')}
Rules of Engagement: {context.get('roe', 'Standard')}

Testing Requirements:
1. Reconnaissance and information gathering
2. Vulnerability identification
3. Exploitation attempts (within scope)
4. Post-exploitation activities
5. Documentation and reporting

Provide penetration test plan.
"""
        return await self._execute_with_llm(task, prompt)

    # Incident Response Handlers
    async def _handle_incident_response(self, task: Task) -> TaskResult:
        """Handle security incident response."""
        context = task.context or {}

        incident = SecurityIncident(
            title=context.get("title", "Security Incident"),
            description=context.get("description", ""),
            severity=IncidentSeverity(context.get("severity", "p3_medium")),
            category=context.get("category", "unknown"),
            affected_systems=context.get("affected_systems", []),
            status=IncidentStatus.TRIAGING,
        )
        self.incidents[incident.id] = incident

        prompt = f"""Respond to security incident:

Incident: {incident.title}
Severity: {incident.severity.value}
Category: {incident.category}
Affected Systems: {incident.affected_systems}
Description: {incident.description}

Response Requirements:
1. Initial triage and severity assessment
2. Containment strategy
3. Evidence preservation
4. Stakeholder communication
5. Escalation if needed

Provide incident response plan.
"""
        result = await self._execute_with_llm(task, prompt)

        if result.success:
            incident.status = IncidentStatus.INVESTIGATING
            incident.acknowledged_at = datetime.now(timezone.utc)
            incident.timeline.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "Incident response initiated",
                    "details": result.output,
                }
            )

        return result

    async def _handle_incident_investigation(self, task: Task) -> TaskResult:
        """Handle incident investigation."""
        context = task.context or {}
        incident_id = context.get("incident_id")
        incident = self.incidents.get(incident_id) if incident_id else None

        prompt = f"""Investigate security incident:

Incident: {incident.title if incident else context.get('title', 'Unknown')}
Category: {incident.category if incident else context.get('category', 'unknown')}
Affected Systems: {incident.affected_systems if incident else context.get('affected_systems', [])}
Timeline: {incident.timeline if incident else []}

Investigation Requirements:
1. Collect and analyze evidence
2. Determine attack vector
3. Identify root cause
4. Assess scope and impact
5. Document findings

Provide investigation findings.
"""
        result = await self._execute_with_llm(task, prompt)

        if result.success and incident:
            incident.timeline.append(
                {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "action": "Investigation completed",
                    "details": result.output,
                }
            )

        return result

    async def _handle_forensics(self, task: Task) -> TaskResult:
        """Handle digital forensics task."""
        context = task.context or {}

        prompt = f"""Conduct digital forensics analysis:

Target: {context.get('target', 'Unknown')}
Evidence Type: {context.get('evidence_type', 'disk_image')}
Chain of Custody: {context.get('chain_of_custody', 'Not specified')}
Objectives: {context.get('objectives', [])}

Forensics Requirements:
1. Evidence acquisition and preservation
2. Timeline reconstruction
3. Artifact analysis
4. Malware analysis (if applicable)
5. Report generation

Provide forensics analysis plan.
"""
        return await self._execute_with_llm(task, prompt)

    # Compliance Handlers
    async def _handle_compliance_assessment(self, task: Task) -> TaskResult:
        """Handle compliance assessment."""
        context = task.context or {}

        prompt = f"""Conduct compliance assessment:

Framework: {context.get('framework', 'SOC2')}
Scope: {context.get('scope', 'Full organization')}
Controls: {context.get('controls', [])}
Previous Assessment: {context.get('previous_assessment', 'N/A')}

Assessment Requirements:
1. Review applicable controls
2. Gather evidence
3. Assess compliance status
4. Identify gaps
5. Recommend remediation

Provide compliance assessment results.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_compliance_audit(self, task: Task) -> TaskResult:
        """Handle compliance audit."""
        context = task.context or {}

        prompt = f"""Support compliance audit:

Audit Type: {context.get('audit_type', 'Internal')}
Framework: {context.get('framework', 'ISO27001')}
Auditor: {context.get('auditor', 'Internal team')}
Scope: {context.get('scope', [])}

Audit Support Requirements:
1. Prepare documentation
2. Gather evidence
3. Schedule interviews
4. Address auditor requests
5. Track findings

Provide audit preparation plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_policy_management(self, task: Task) -> TaskResult:
        """Handle security policy management."""
        context = task.context or {}
        action = context.get("action", "review")

        prompt = f"""Manage security policy:

Action: {action}
Policy Type: {context.get('policy_type', 'general')}
Current Policy: {context.get('current_policy', 'N/A')}
Requirements: {context.get('requirements', [])}

Policy Management Requirements:
1. Review current policy
2. Identify gaps and improvements
3. Align with frameworks
4. Update policy content
5. Plan implementation

Provide policy recommendations.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_access_review(self, task: Task) -> TaskResult:
        """Handle access review."""
        context = task.context or {}

        review = AccessReview(
            name=context.get("name", "Access Review"),
            review_type=context.get("review_type", "user"),
            scope=context.get("scope", []),
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )
        self.access_reviews[review.id] = review

        prompt = f"""Conduct access review:

Review Type: {review.review_type}
Scope: {review.scope}
Users/Accounts: {context.get('accounts', [])}
Systems: {context.get('systems', [])}

Review Requirements:
1. Identify all access rights
2. Validate business justification
3. Check for excessive privileges
4. Identify dormant accounts
5. Recommend changes

Provide access review findings.
"""
        result = await self._execute_with_llm(task, prompt)

        if result.success:
            review.status = "completed"
            review.completed_at = datetime.now(timezone.utc)

        return result

    # Security Operations Handlers
    async def _handle_security_monitoring(self, task: Task) -> TaskResult:
        """Handle security monitoring setup."""
        context = task.context or {}

        prompt = f"""Configure security monitoring:

Scope: {context.get('scope', 'Full environment')}
Data Sources: {context.get('data_sources', [])}
Use Cases: {context.get('use_cases', [])}
Alerting Requirements: {context.get('alerting', {})}

Monitoring Requirements:
1. Define monitoring scope
2. Configure data collection
3. Create detection rules
4. Set up alerting
5. Define response procedures

Provide monitoring configuration plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_siem_operations(self, task: Task) -> TaskResult:
        """Handle SIEM operations."""
        context = task.context or {}

        prompt = f"""Manage SIEM operations:

Operation: {context.get('operation', 'optimization')}
Current State: {context.get('current_state', {})}
Issues: {context.get('issues', [])}

SIEM Requirements:
1. Review current configuration
2. Optimize detection rules
3. Reduce false positives
4. Improve coverage
5. Enhance correlation

Provide SIEM optimization plan.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_security_automation(self, task: Task) -> TaskResult:
        """Handle security automation."""
        context = task.context or {}

        prompt = f"""Design security automation:

Automation Goal: {context.get('goal', 'Incident response automation')}
Current Processes: {context.get('current_processes', [])}
Tools: {context.get('tools', [])}
Constraints: {context.get('constraints', [])}

Automation Requirements:
1. Identify automation opportunities
2. Design workflows
3. Define triggers and actions
4. Plan integration
5. Measure effectiveness

Provide automation design.
"""
        return await self._execute_with_llm(task, prompt)

    # AppSec Handlers
    async def _handle_code_review(self, task: Task) -> TaskResult:
        """Handle security code review."""
        context = task.context or {}

        prompt = f"""Conduct security code review:

Repository: {context.get('repository', 'Unknown')}
Language: {context.get('language', 'Unknown')}
Files: {context.get('files', [])}
Focus Areas: {context.get('focus_areas', ['authentication', 'authorization', 'input_validation'])}

Review Requirements:
1. Identify security vulnerabilities
2. Check for OWASP Top 10 issues
3. Review authentication/authorization
4. Assess input validation
5. Check secrets handling

Provide code review findings.
"""
        return await self._execute_with_llm(task, prompt)

    async def _handle_sast_scan(self, task: Task) -> TaskResult:
        """Handle SAST scanning."""
        context = task.context or {}

        scan = SecurityScan(
            name=context.get("name", "SAST Scan"),
            scan_type=ScanType.CODE_ANALYSIS,
            target=context.get("repository", ""),
            status=ScanStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self.scans[scan.id] = scan

        prompt = f"""Execute SAST scan:

Repository: {scan.target}
Language: {context.get('language', 'auto-detect')}
Branch: {context.get('branch', 'main')}
Tool: {context.get('tool', 'auto')}

Scan Requirements:
1. Configure scanner
2. Execute analysis
3. Categorize findings
4. Filter false positives
5. Prioritize vulnerabilities

Provide SAST scan plan and expected outputs.
"""
        result = await self._execute_with_llm(task, prompt)

        scan.status = ScanStatus.COMPLETED if result.success else ScanStatus.FAILED
        scan.completed_at = datetime.now(timezone.utc)

        return result

    async def _handle_dast_scan(self, task: Task) -> TaskResult:
        """Handle DAST scanning."""
        context = task.context or {}

        scan = SecurityScan(
            name=context.get("name", "DAST Scan"),
            scan_type=ScanType.PENETRATION,
            target=context.get("url", ""),
            status=ScanStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self.scans[scan.id] = scan

        prompt = f"""Execute DAST scan:

Target URL: {scan.target}
Authentication: {context.get('authentication', 'None')}
Scope: {context.get('scope', 'Full application')}
Exclusions: {context.get('exclusions', [])}

Scan Requirements:
1. Configure scanner
2. Define crawl scope
3. Execute dynamic testing
4. Validate findings
5. Report vulnerabilities

Provide DAST scan configuration.
"""
        result = await self._execute_with_llm(task, prompt)

        scan.status = ScanStatus.COMPLETED if result.success else ScanStatus.FAILED
        scan.completed_at = datetime.now(timezone.utc)

        return result

    async def _handle_dependency_scan(self, task: Task) -> TaskResult:
        """Handle dependency scanning."""
        context = task.context or {}

        scan = SecurityScan(
            name=context.get("name", "Dependency Scan"),
            scan_type=ScanType.DEPENDENCY,
            target=context.get("repository", ""),
            status=ScanStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        self.scans[scan.id] = scan

        prompt = f"""Execute dependency scan:

Repository: {scan.target}
Package Manager: {context.get('package_manager', 'auto-detect')}
Manifest Files: {context.get('manifest_files', [])}

Scan Requirements:
1. Identify all dependencies
2. Check for known vulnerabilities
3. Assess license compliance
4. Identify outdated packages
5. Recommend updates

Provide dependency scan results.
"""
        result = await self._execute_with_llm(task, prompt)

        scan.status = ScanStatus.COMPLETED if result.success else ScanStatus.FAILED
        scan.completed_at = datetime.now(timezone.utc)

        return result

    async def _execute_with_llm(self, task: Task, prompt: str) -> TaskResult:
        """Execute task using LLM via reason() method."""
        try:
            response = await self.reason(prompt, task.context)
            return TaskResult(
                task_id=task.id,
                success=True,
                output=response,
            )
        except Exception as e:
            logger.error(f"LLM execution failed: {e}")
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
            )

    # Sentinel Bridge Methods
    async def sentinel_security_action(
        self,
        action: str,
        parameters: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute a security action via Sentinel Guardian agent.

        Args:
            action: Security action (block_ip, unblock_ip, quarantine, etc.)
            parameters: Action parameters

        Returns:
            Action result dictionary
        """
        if not self._sentinel_bridge or not self._sentinel_bridge.is_connected:
            return {"success": False, "error": "Sentinel not connected"}

        return await self._sentinel_bridge.route_to_agent("guardian", action, parameters)

    async def sentinel_health_check(self) -> Dict[str, Any]:
        """
        Check Sentinel platform health.

        Returns:
            Health status dictionary
        """
        if not self._sentinel_bridge or not self._sentinel_bridge.is_connected:
            return {"healthy": False, "error": "Sentinel not connected"}

        return await self._sentinel_bridge.get_agent_health()

    async def sentinel_discovery_scan(
        self,
        network: Optional[str] = None,
        scan_type: str = "quick",
    ) -> Dict[str, Any]:
        """
        Run an asset discovery scan via Sentinel.

        Args:
            network: Optional network CIDR to scan
            scan_type: Scan type (quick or full)

        Returns:
            Scan results
        """
        if not self._sentinel_bridge or not self._sentinel_bridge.is_connected:
            return {"success": False, "error": "Sentinel not connected"}

        return await self._sentinel_bridge.route_to_agent(
            "discovery",
            "scan_network",
            {"network": network, "scan_type": scan_type},
        )

    async def sentinel_compliance_check(
        self,
        framework: str = "CIS",
        scope: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Run compliance check via Sentinel.

        Args:
            framework: Compliance framework (CIS, NIST, etc.)
            scope: Optional scope of check

        Returns:
            Compliance results
        """
        if not self._sentinel_bridge or not self._sentinel_bridge.is_connected:
            return {"success": False, "error": "Sentinel not connected"}

        return await self._sentinel_bridge.route_to_agent(
            "compliance",
            "assess",
            {"framework": framework, "scope": scope or []},
        )

    def get_sentinel_stats(self) -> Dict[str, Any]:
        """
        Get Sentinel bridge statistics.

        Returns:
            Bridge statistics dictionary
        """
        if not self._sentinel_bridge:
            return {
                "connected": False,
                "message": "Sentinel bridge not initialized",
            }
        return self._sentinel_bridge.stats

    # Metrics and reporting
    def get_security_metrics(self) -> SecurityMetrics:
        """Get current security metrics."""
        now = datetime.now(timezone.utc)

        # Count vulnerabilities
        open_vulns = [
            v for v in self.vulnerabilities.values() if v.status == VulnerabilityStatus.OPEN
        ]
        critical_vulns = [v for v in open_vulns if v.severity == ThreatSeverity.CRITICAL]
        high_vulns = [v for v in open_vulns if v.severity == ThreatSeverity.HIGH]

        # Count threats
        active_threats = [
            t
            for t in self.threats.values()
            if t.status not in [ThreatStatus.RESOLVED, ThreatStatus.FALSE_POSITIVE]
        ]

        # Count incidents
        open_incidents = [i for i in self.incidents.values() if i.status != IncidentStatus.CLOSED]

        # Count compliant controls
        compliant = len(
            [c for c in self.controls.values() if c.status == ComplianceStatus.COMPLIANT]
        )
        non_compliant = len(
            [c for c in self.controls.values() if c.status == ComplianceStatus.NON_COMPLIANT]
        )
        total_controls = len(self.controls)

        return SecurityMetrics(
            timestamp=now,
            open_vulnerabilities=len(open_vulns),
            critical_vulnerabilities=len(critical_vulns),
            high_vulnerabilities=len(high_vulns),
            active_threats=len(active_threats),
            open_incidents=len(open_incidents),
            controls_compliant=compliant,
            controls_non_compliant=non_compliant,
            compliance_score=(compliant / total_controls * 100) if total_controls > 0 else 0,
        )

    def get_security_posture(self) -> Dict[str, Any]:
        """Get overall security posture."""
        metrics = self.get_security_metrics()

        # Calculate security score (simplified)
        vuln_score = max(
            0, 100 - (metrics.critical_vulnerabilities * 20 + metrics.high_vulnerabilities * 10)
        )
        threat_score = max(0, 100 - (metrics.active_threats * 15))
        incident_score = max(0, 100 - (metrics.open_incidents * 10))
        compliance_score = metrics.compliance_score

        overall_score = (vuln_score + threat_score + incident_score + compliance_score) / 4

        return {
            "overall_score": overall_score,
            "vulnerability_score": vuln_score,
            "threat_score": threat_score,
            "incident_score": incident_score,
            "compliance_score": compliance_score,
            "sentinel_connected": self._sentinel_connected,
            "metrics": {
                "open_vulnerabilities": metrics.open_vulnerabilities,
                "active_threats": metrics.active_threats,
                "open_incidents": metrics.open_incidents,
                "compliance_rate": metrics.compliance_score,
            },
        }
