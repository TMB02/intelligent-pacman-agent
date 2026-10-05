"""Minimax and Alpha-Beta search for the intelligent Pac-Man agent."""

from dataclasses import dataclass
from math import inf
from time import perf_counter

from .state import (
    SimulationState,
    apply_ghost_actions,
    apply_pacman_action,
    ghost_action_combinations,
    legal_actions_from_state,
)


@dataclass
class SearchMetrics:
    nodes_visited: int = 0
    nodes_pruned: int = 0
    decision_time_ms: float = 0.0


@dataclass(frozen=True)
class EvaluationWeights:
    target_progress: float = 8.0
    nearest_target: float = 1.5
    ghost_distance: float = 5.0
    collision: float = 1000.0
    vulnerable_ghost: float = 3.0
    mobility: float = 1.0


class MinimaxAgent:
    """Choose actions with adversarial ghost simulation.

    ``use_alpha_beta=True`` uses the same Minimax recurrence with alpha-beta
    bounds.  Set it to False for a baseline comparison in experiments.
    """

    def __init__(self, depth: int = 3, use_alpha_beta: bool = True, weights: EvaluationWeights | None = None):
        if depth < 1:
            raise ValueError("Search depth must be at least 1")
        self.depth = depth
        self.use_alpha_beta = use_alpha_beta
        self.weights = weights or EvaluationWeights()
        self.last_metrics = SearchMetrics()
        self.last_action_values: dict[str, float] = {}

    def choose_action(self, state: SimulationState) -> str:
        """Return the best legal Pac-Man action and record search metrics."""

        started = perf_counter()
        self.last_metrics = SearchMetrics()
        self.last_action_values = {}
        actions = legal_actions_from_state(state, state.pacman)
        if not actions:
            self.last_metrics.decision_time_ms = (perf_counter() - started) * 1000
            return "none"

        best_action = actions[0]
        best_value = -inf
        for action in actions:
            child = apply_pacman_action(state, action)
            value = self._ghost_turn(child, self.depth - 1, -inf, inf)
            self.last_action_values[action] = value
            if value > best_value:
                best_value = value
                best_action = action
        self.last_metrics.decision_time_ms = (perf_counter() - started) * 1000
        return best_action

    def _pacman_turn(self, state: SimulationState, depth: int, alpha: float, beta: float) -> float:
        self.last_metrics.nodes_visited += 1
        if depth <= 0 or self._terminal(state):
            return self.evaluate(state)
        actions = legal_actions_from_state(state, state.pacman)
        if not actions:
            return self.evaluate(state)
        value = -inf
        for action in actions:
            value = max(value, self._ghost_turn(apply_pacman_action(state, action), depth - 1, alpha, beta))
            if self.use_alpha_beta:
                alpha = max(alpha, value)
                if alpha >= beta:
                    self.last_metrics.nodes_pruned += 1
                    break
        return value

    def _ghost_turn(self, state: SimulationState, depth: int, alpha: float, beta: float) -> float:
        self.last_metrics.nodes_visited += 1
        if depth < 0 or self._terminal(state):
            return self.evaluate(state)
        combinations = ghost_action_combinations(state)
        if not combinations:
            return self.evaluate(state)
        value = inf
        for actions in combinations:
            value = min(value, self._pacman_turn(apply_ghost_actions(state, actions), depth, alpha, beta))
            if self.use_alpha_beta:
                beta = min(beta, value)
                if alpha >= beta:
                    self.last_metrics.nodes_pruned += 1
                    break
        return value

    def _terminal(self, state: SimulationState) -> bool:
        return any(ghost.active and ghost.position == state.pacman and not ghost.vulnerable for ghost in state.ghosts)

    def evaluate(self, state: SimulationState) -> float:
        """Explainable heuristic: progress, targets, mobility, and ghost risk."""

        if self._terminal(state):
            return -self.weights.collision

        value = state.collected_targets * self.weights.target_progress
        targets = state.pellets | state.energizers
        if targets:
            nearest = min(self._manhattan(state.pacman, target) for target in targets)
            value -= nearest * self.weights.nearest_target
        value += len(legal_actions_from_state(state, state.pacman)) * self.weights.mobility

        for ghost in state.ghosts:
            distance = self._manhattan(state.pacman, ghost.position)
            if ghost.vulnerable:
                value += max(0, 12 - distance) * self.weights.vulnerable_ghost
            elif ghost.active:
                value += (distance - 4) * self.weights.ghost_distance
        return value

    @staticmethod
    def _manhattan(first: tuple[int, int], second: tuple[int, int]) -> int:
        return abs(first[0] - second[0]) + abs(first[1] - second[1])
