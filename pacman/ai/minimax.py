"""Minimax and Alpha-Beta search for the intelligent Pac-Man agent."""

from dataclasses import dataclass
from collections import deque
from math import inf
from time import perf_counter

from .state import (
    SimulationState,
    apply_ghost_actions,
    apply_pacman_action,
    ghost_action_combinations,
    legal_actions_from_state,
    move_position,
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
    dead_end: float = 120.0
    corridor_trap: float = 160.0
    energizer_strategy: float = 10.0
    route_following: float = 120.0
    panic_distance: float = 60.0


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
        self._distance_cache: dict[tuple[tuple[int, int], frozenset[tuple[int, int]]], int] = {}

    def choose_action(self, state: SimulationState) -> str:
        """Return the best legal Pac-Man action and record search metrics."""

        started = perf_counter()
        self.last_metrics = SearchMetrics()
        self.last_action_values = {}
        self._distance_cache.clear()
        actions = legal_actions_from_state(state, state.pacman)
        if not actions:
            self.last_metrics.decision_time_ms = (perf_counter() - started) * 1000
            return "none"

        safe_actions = tuple(action for action in actions if not self._unsafe_one_step(state, action))
        actions_to_score = safe_actions or actions
        route_action = self._risk_aware_route_action(state, actions_to_score)
        dangerous_distances = [
            self._manhattan(state.pacman, ghost.position)
            for ghost in state.ghosts
            if ghost.active and not ghost.vulnerable
        ]
        nearest_danger = min(dangerous_distances, default=999)
        panic_mode = nearest_danger <= 6
        if nearest_danger <= 4:
            actions_to_score = (
                max(
                    actions_to_score,
                    key=lambda action: self._escape_distance_bonus(state, action),
                ),
            )

        best_action = actions_to_score[0]
        best_value = -inf
        for action in actions_to_score:
            child = apply_pacman_action(state, action)
            value = self._ghost_turn(child, self.depth - 1, -inf, inf)
            if action == route_action:
                value += self.weights.route_following
            if panic_mode:
                value += self._escape_distance_bonus(state, action)
            self.last_action_values[action] = value
            if value > best_value:
                best_value = value
                best_action = action
        self.last_metrics.decision_time_ms = (perf_counter() - started) * 1000
        return best_action

    def _escape_distance_bonus(self, state: SimulationState, action: str) -> float:
        """Prefer actions that increase the nearest dangerous-ghost distance."""

        position = move_position(state, state.pacman, action)
        distances = [
            self._manhattan(position, ghost.position)
            for ghost in state.ghosts
            if ghost.active and not ghost.vulnerable
        ]
        return min(distances, default=8) * self.weights.panic_distance

    def _risk_aware_route_action(
        self, state: SimulationState, actions: tuple[str, ...]
    ) -> str | None:
        """Find a first step toward a reachable target outside ghost danger."""

        dangerous_distances = [
            self._manhattan(state.pacman, ghost.position)
            for ghost in state.ghosts
            if ghost.active and not ghost.vulnerable
        ]
        danger_nearby = bool(dangerous_distances)
        vulnerable_ghosts = frozenset(
            ghost.position for ghost in state.ghosts if ghost.active and ghost.vulnerable
        )
        if vulnerable_ghosts:
            targets = vulnerable_ghosts
        else:
            targets = state.energizers if danger_nearby and state.energizers else state.pellets | state.energizers
        if not targets:
            return None
        queue = deque()
        visited = {state.pacman}
        for action in actions:
            position = move_position(state, state.pacman, action)
            if not self._position_is_dangerous(state, position):
                queue.append((position, action))
                visited.add(position)
        while queue:
            position, first_action = queue.popleft()
            if position in targets:
                return first_action
            for action in legal_actions_from_state(state, position):
                next_position = move_position(state, position, action)
                if next_position in visited or self._position_is_dangerous(state, next_position):
                    continue
                visited.add(next_position)
                queue.append((next_position, first_action))
        return None

    def _position_is_dangerous(
        self,
        state: SimulationState,
        position: tuple[int, int],
    ) -> bool:
        if position in state.energizers:
            return False
        return any(
            ghost.active
            and not ghost.vulnerable
            and self._manhattan(position, ghost.position) <= 4
            for ghost in state.ghosts
        )

    def _unsafe_one_step(self, state: SimulationState, action: str) -> bool:
        """Reject an action if a bounded worst-case ghost response is lethal."""

        child = apply_pacman_action(state, action)
        if self._terminal(child):
            return True
        responses = ghost_action_combinations(child, max_combinations=1)
        if not responses:
            return False
        response_state = apply_ghost_actions(child, responses[0])
        return any(
            ghost.active
            and not ghost.vulnerable
            and self._manhattan(ghost.position, response_state.pacman) <= 2
            for ghost in response_state.ghosts
        )

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
        targets = state.pellets | state.energizers | frozenset(
            ghost.position for ghost in state.ghosts if ghost.active and ghost.vulnerable
        )
        if targets:
            nearest = self._nearest_target_distance(state, state.pacman, targets)
            value -= nearest * self.weights.nearest_target

        escape_routes = len(legal_actions_from_state(state, state.pacman))
        value += escape_routes * self.weights.mobility
        if escape_routes <= 1:
            value -= self.weights.dead_end

            dangerous_distances = [
                self._manhattan(state.pacman, ghost.position)
                for ghost in state.ghosts
                if ghost.active and not ghost.vulnerable
            ]
            nearest_danger = min(dangerous_distances, default=999)
            if nearest_danger <= 10:
                value -= (11 - nearest_danger) * self.weights.corridor_trap

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
            nearest_energizer = self._nearest_target_distance(state, state.pacman, state.energizers)
            value += max(0, 8 - nearest_energizer) * self.weights.energizer_strategy
        return value

    def _nearest_target_distance(
        self,
        state: SimulationState,
        start: tuple[int, int],
        targets: frozenset[tuple[int, int]],
    ) -> int:
        """Return the shortest reachable corridor distance to any target."""

        cache_key = (start, targets)
        if cache_key in self._distance_cache:
            return self._distance_cache[cache_key]
        if start in targets:
            self._distance_cache[cache_key] = 0
            return 0
        queue = deque([(start, 0)])
        visited = {start}
        while queue:
            position, distance = queue.popleft()
            for action in legal_actions_from_state(state, position):
                next_position = move_position(state, position, action)
                if next_position in visited:
                    continue
                if next_position in targets:
                    result = distance + 1
                    self._distance_cache[cache_key] = result
                    return result
                visited.add(next_position)
                queue.append((next_position, distance + 1))
        self._distance_cache[cache_key] = 999
        return 999

    @staticmethod
    def _manhattan(first: tuple[int, int], second: tuple[int, int]) -> int:
        return abs(first[0] - second[0]) + abs(first[1] - second[1])
