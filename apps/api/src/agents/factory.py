from src.agents.base import Agent
from src.agents.fact_checker import FactCheckerAgent
from src.agents.orchestrator import OrchestratorAgent
from src.agents.providers import AIProvider
from src.agents.researcher import ResearcherAgent
from src.agents.writer import WriterAgent
from src.db.models import AgentRole


class AgentFactory:
    """Factory creating concrete agent instances based on their role."""

    @staticmethod
    def create(role: AgentRole, provider: AIProvider) -> Agent:
        """Instantiate and return the appropriate concrete Agent."""
        if role == AgentRole.ORCHESTRATOR:
            return OrchestratorAgent(provider)
        elif role == AgentRole.RESEARCHER:
            return ResearcherAgent(provider)
        elif role == AgentRole.FACT_CHECKER:
            return FactCheckerAgent(provider)
        elif role == AgentRole.WRITER:
            return WriterAgent(provider)
        else:
            raise ValueError(f"Unsupported agent role: '{role}'")
