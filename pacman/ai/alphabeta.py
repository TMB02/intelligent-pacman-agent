"""Alpha-Beta pruning entry point for the intelligent Pac-Man agent."""

from .minimax import EvaluationWeights, MinimaxAgent


class AlphaBetaAgent(MinimaxAgent):
    """Minimax agent configured to prune dominated adversarial branches."""

    def __init__(self, depth: int = 3, weights: EvaluationWeights | None = None) -> None:
        super().__init__(depth=depth, use_alpha_beta=True, weights=weights)
