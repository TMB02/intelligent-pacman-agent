"""AI decision-making layer for the Pac-Man environment."""

from .alphabeta import AlphaBetaAgent
from .minimax import EvaluationWeights, MinimaxAgent, SearchMetrics
from .state import SimulationState, extract_state


class IntelligentAgent:
    """Bridge the live Pygame environment to the pure search implementation."""

    def __init__(self, depth: int = 2) -> None:
        self.search = AlphaBetaAgent(depth=depth)

    def choose_action(self, pacman, ghosts, loader, seeds=None) -> str:
        state: SimulationState = extract_state(pacman, ghosts, loader, seeds)
        return self.search.choose_action(state)

    @property
    def metrics(self) -> SearchMetrics:
        return self.search.last_metrics

    @property
    def action_values(self) -> dict[str, float]:
        return dict(self.search.last_action_values)


__all__ = [
    "EvaluationWeights",
    "AlphaBetaAgent",
    "IntelligentAgent",
    "MinimaxAgent",
    "SearchMetrics",
    "SimulationState",
    "extract_state",
]
