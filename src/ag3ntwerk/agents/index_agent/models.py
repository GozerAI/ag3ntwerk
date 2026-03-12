"""
Data models for the Index (Index) agent.

This module defines the core data structures for data governance,
quality management, and knowledge organization.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def _utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class DataQualityLevel(Enum):
    """Data quality classification levels."""

    CRITICAL = "critical"  # Production-critical, highest quality standards
    HIGH = "high"  # Important business data, strict quality
    MEDIUM = "medium"  # Standard business data
    LOW = "low"  # Informal or derived data
    UNKNOWN = "unknown"  # Not yet classified


class DataSensitivity(Enum):
    """Data sensitivity classification."""

    PUBLIC = "public"  # Can be shared externally
    INTERNAL = "internal"  # Internal use only
    CONFIDENTIAL = "confidential"  # Restricted access
    SECRET = "secret"  # Highly restricted
    PII = "pii"  # Personally identifiable information
    PHI = "phi"  # Protected health information


class SchemaStatus(Enum):
    """Schema lifecycle status."""

    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class LineageType(Enum):
    """Types of data lineage relationships."""

    DERIVED_FROM = "derived_from"  # Data derived from source
    COPIED_FROM = "copied_from"  # Direct copy
    AGGREGATED_FROM = "aggregated_from"  # Aggregation
    TRANSFORMED_FROM = "transformed_from"  # Transformation applied
    JOINED_WITH = "joined_with"  # Joined datasets
    FILTERED_FROM = "filtered_from"  # Subset of source


@dataclass
class SchemaField:
    """Represents a field in a data schema."""

    name: str
    data_type: str
    description: str = ""
    required: bool = True
    nullable: bool = False
    default_value: Any = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "data_type": self.data_type,
            "description": self.description,
            "required": self.required,
            "nullable": self.nullable,
            "default_value": self.default_value,
            "constraints": self.constraints,
            "metadata": self.metadata,
        }


@dataclass
class Schema:
    """Represents a data schema definition."""

    id: str
    name: str
    version: str = "1.0.0"
    description: str = ""
    fields: List[SchemaField] = field(default_factory=list)
    status: SchemaStatus = SchemaStatus.DRAFT
    owner: str = ""
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_field(self, schema_field: SchemaField) -> None:
        """Add a field to the schema."""
        self.fields.append(schema_field)
        self.updated_at = _utcnow()

    def get_field(self, name: str) -> Optional[SchemaField]:
        """Get a field by name."""
        for f in self.fields:
            if f.name == name:
                return f
        return None

    def validate_data(self, data: Dict[str, Any]) -> List[str]:
        """Validate data against the schema. Returns list of errors."""
        errors = []

        # Check required fields
        for f in self.fields:
            if f.required and f.name not in data:
                errors.append(f"Missing required field: {f.name}")
            elif f.name in data:
                value = data[f.name]
                if value is None and not f.nullable:
                    errors.append(f"Field {f.name} cannot be null")

        # Check for unknown fields
        known_fields = {f.name for f in self.fields}
        for key in data.keys():
            if key not in known_fields:
                errors.append(f"Unknown field: {key}")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "fields": [f.to_dict() for f in self.fields],
            "status": self.status.value,
            "owner": self.owner,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class DataQualityRule:
    """A data quality rule for validation."""

    id: str
    name: str
    description: str = ""
    rule_type: str = "custom"  # completeness, accuracy, consistency, etc.
    expression: str = ""  # Rule expression or condition
    severity: str = "warning"  # error, warning, info
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "rule_type": self.rule_type,
            "expression": self.expression,
            "severity": self.severity,
            "enabled": self.enabled,
            "metadata": self.metadata,
        }


@dataclass
class QualityCheckResult:
    """Result of a data quality check."""

    rule_id: str
    rule_name: str
    passed: bool
    severity: str
    message: str = ""
    affected_records: int = 0
    total_records: int = 0
    checked_at: datetime = field(default_factory=_utcnow)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate as percentage."""
        if self.total_records == 0:
            return 100.0
        return ((self.total_records - self.affected_records) / self.total_records) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "affected_records": self.affected_records,
            "total_records": self.total_records,
            "pass_rate": self.pass_rate,
            "checked_at": self.checked_at.isoformat(),
            "details": self.details,
        }


@dataclass
class Dataset:
    """Represents a managed dataset."""

    id: str
    name: str
    description: str = ""
    schema_id: Optional[str] = None
    quality_level: DataQualityLevel = DataQualityLevel.UNKNOWN
    sensitivity: DataSensitivity = DataSensitivity.INTERNAL
    owner: str = ""
    steward: str = ""
    location: str = ""  # URI or path
    format: str = ""  # csv, parquet, json, etc.
    row_count: int = 0
    size_bytes: int = 0
    quality_rules: List[str] = field(default_factory=list)  # Rule IDs
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    last_quality_check: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "schema_id": self.schema_id,
            "quality_level": self.quality_level.value,
            "sensitivity": self.sensitivity.value,
            "owner": self.owner,
            "steward": self.steward,
            "location": self.location,
            "format": self.format,
            "row_count": self.row_count,
            "size_bytes": self.size_bytes,
            "quality_rules": self.quality_rules,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_quality_check": (
                self.last_quality_check.isoformat() if self.last_quality_check else None
            ),
            "metadata": self.metadata,
        }


@dataclass
class LineageEdge:
    """Represents a lineage relationship between datasets."""

    id: str
    source_id: str
    target_id: str
    lineage_type: LineageType
    description: str = ""
    transformation: str = ""  # Description of transformation applied
    created_at: datetime = field(default_factory=_utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "lineage_type": self.lineage_type.value,
            "description": self.description,
            "transformation": self.transformation,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class DataCatalogEntry:
    """Entry in the data catalog."""

    id: str
    name: str
    entry_type: str  # dataset, schema, report, dashboard, etc.
    description: str = ""
    location: str = ""
    owner: str = ""
    tags: List[str] = field(default_factory=list)
    sensitivity: DataSensitivity = DataSensitivity.INTERNAL
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "entry_type": self.entry_type,
            "description": self.description,
            "location": self.location,
            "owner": self.owner,
            "tags": self.tags,
            "sensitivity": self.sensitivity.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "metadata": self.metadata,
        }


@dataclass
class KnowledgeArticle:
    """A knowledge base article (merged from CKO)."""

    id: str
    title: str
    content: str
    category: str = ""
    tags: List[str] = field(default_factory=list)
    author: str = ""
    status: str = "draft"  # draft, published, archived
    version: str = "1.0"
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)
    view_count: int = 0
    helpful_votes: int = 0
    related_articles: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category,
            "tags": self.tags,
            "author": self.author,
            "status": self.status,
            "version": self.version,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "view_count": self.view_count,
            "helpful_votes": self.helpful_votes,
            "related_articles": self.related_articles,
            "metadata": self.metadata,
        }
