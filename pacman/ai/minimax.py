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
    """Tunable, explainable weights for state evaluation."""

    score_reward: float = 1.0
    target_progress: float = 2.0
    nearest_target: float = 1.5
    ghost_distance: float = 2.5
    ghost_threat: float = 30.0
    collision: float = 5000.0
    vulnerable_ghost: float = 20.0
    mobility: float = 2.0
    escape_route: float = 4.0
    dead_end: float = 20.0
    energizer_strategy: float = 10.0


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
        """Score progress while strongly preferring survivable escape routes.

        Near-ghost danger is non-linear: four cells away is usually acceptable,
        while one cell away is strategically disastrous unless the ghost is
        vulnerable. This prevents a tempting pellet from outweighing survival.
        """

        if self._terminal(state):
            return -self.weights.collision

        value = state.score * self.weights.score_reward
        value += state.collected_targets * self.weights.target_progress
        targets = state.pellets | state.energizers
        if targets:
            nearest = min(self._manhattan(state.pacman, target) for target in targets)
            value -= nearest * self.weights.nearest_target

        escape_routes = len(legal_actions_from_state(state, state.pacman))
        value += escape_routes * self.weights.mobility
        if escape_routes <= 1:
            value -= self.weights.dead_end

        for ghost in state.ghosts:
            distance = self._manhattan(state.pacman, ghost.position)
            if ghost.vulnerable:
                value += max(0, 10 - distance) * self.weights.vulnerable_ghost
            elif ghost.active:
                value += min(distance, 12) * self.weights.ghost_distance
                if distance <= 1:
                    value -= self.weights.collision
                elif distance <= 5:
                    value -= (6 - distance) ** 2 * self.weights.ghost_threat
                    value += escape_routes * self.weights.escape_route

        dangerous_ghost_nearby = any(
            ghost.active and not ghost.vulnerable and self._manhattan(state.pacman, ghost.position) <= 7
            for ghost in state.ghosts
        )
        if dangerous_ghost_nearby and state.energizers:
            nearest_energizer = min(self._manhattan(state.pacman, target) for target in state.energizers)
            value += max(0, 8 - nearest_energizer) * self.weights.energizer_strategy
        return value

    @staticmethod
    def _manhattan(first: tuple[int, int], second: tuple[int, int]) -> int:
        return abs(first[0] - second[0]) + abs(first[1] - second[1])
