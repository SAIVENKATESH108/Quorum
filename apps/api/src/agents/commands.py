import logging
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from src.agents.base import Agent, AgentResult
from src.db.models import AgentTask

logger = logging.getLogger(__name__)


@dataclass
class AgentTaskCommand:
    """
    Command pattern encapsulating a unit of work dispatched to an agent:
    - Serializable for message queuing and persistence
    - Encapsulates execution against an injected Agent and AgentTask model
    - Determines retryability of failures for resilient re-enqueuing
    """

    agent_run_id: uuid.UUID
    task_type: str
    payload: Dict[str, Any] = field(default_factory=dict)
    command_id: uuid.UUID = field(default_factory=uuid.uuid4)
    retry_count: int = 0
    max_retries: int = 3

    async def execute(self, agent: Agent, task_model: AgentTask) -> AgentResult:
        """Execute the command using the specified agent."""
        logger.info(
            f"[COMMAND] Executing command {self.command_id} (run_id: {self.agent_run_id}, "
            f"task_type: {self.task_type}, attempt: {self.retry_count + 1}/{self.max_retries})"
        )
        try:
            result = await agent.run(task_model)
            return result
        except Exception as exc:
            logger.error(f"[COMMAND] Execution error for command {self.command_id}: {exc}")
            return AgentResult(success=False, error=str(exc))

    def is_retryable(self, error: Optional[Exception | str] = None) -> bool:
        """
        Determine if this command can be safely retried.
        Enforces maximum retry limit and inspects fatal error conditions.
        """
        if self.retry_count >= self.max_retries:
            return False

        if error:
            err_msg = str(error).lower()
            # Non-retryable error patterns
            if "unsupported agent role" in err_msg or "invalid schema" in err_msg:
                return False

        return True

    def increment_retry(self) -> None:
        """Increment the retry attempt counter."""
        self.retry_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Serialize command to JSON-compatible dictionary."""
        return {
            "command_id": str(self.command_id),
            "agent_run_id": str(self.agent_run_id),
            "task_type": self.task_type,
            "payload": self.payload,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentTaskCommand":
        """Deserialize command from dictionary."""
        return cls(
            command_id=uuid.UUID(data["command_id"]) if "command_id" in data else uuid.uuid4(),
            agent_run_id=uuid.UUID(data["agent_run_id"]),
            task_type=data["task_type"],
            payload=data.get("payload", {}),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3),
        )
