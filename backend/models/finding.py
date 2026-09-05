"""Models representing individual review findings"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ReviewFinding(BaseModel):
    """A single issue identified by an agent (or the validator)"""

    severity: Severity
    file: str
    line: int | None = None
    title: str
    description: str
    evidence: str
    suggestion: str
    source_agents: list[str] = Field(default_factory=list)
