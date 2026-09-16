from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from src.db.models import AgentRole, AgentTask

if TYPE_CHECKING:
    from src.agents.providers import AIProvider


@dataclass
class AgentResult:
    """Standardized execution outcome returned by an Agent."""
    success: bool
    output: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TaskNode:
    """A node in the Orchestration task DAG."""
    id: str
    description: str
    task_type: str
    agent_role: AgentRole
    depends_on: List[str] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["agent_role"] = self.agent_role.value if isinstance(self.agent_role, AgentRole) else self.agent_role
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskNode":
        role = data.get("agent_role")
        if isinstance(role, str):
            role = AgentRole(role)
        return cls(
            id=data["id"],
            description=data.get("description", ""),
            task_type=data.get("task_type", "research"),
            agent_role=role,
            depends_on=data.get("depends_on", []),
            payload=data.get("payload", {}),
        )


class Agent(ABC):
    """Abstract base class for all Quorum multi-agent workers."""

    role: AgentRole

    def __init__(self, provider: "AIProvider"):
        self.provider = provider

    @abstractmethod
    async def run(self, task: AgentTask) -> AgentResult:
        """Execute the assigned task and return an AgentResult."""
        pass
