from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class QualityIssue:
    id: str
    category: str        # 'missing_value', 'duplicate', 'invalid_format', 'inconsistency', 'statistical_anomaly'
    severity: str        # 'critical', 'warning', 'info'
    column: Optional[str]
    title: str
    description: str
    row_indices: List[int] = field(default_factory=list)  # 1-based row numbers
    affected_count: int = 0
    sample_values: List[Any] = field(default_factory=list)
    suggested_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "severity": self.severity,
            "column": self.column,
            "title": self.title,
            "description": self.description,
            "row_indices": self.row_indices,
            "affected_count": self.affected_count or len(self.row_indices),
            "sample_values": self.sample_values,
            "suggested_action": self.suggested_action,
            "metadata": self.metadata,
        }
