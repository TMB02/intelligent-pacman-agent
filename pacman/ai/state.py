"""Lightweight, immutable states used by the Pac-Man search agent.

The live Pygame objects are deliberately not passed into Minimax.  Search works
on these small tuples so exploring a branch never mutates the running game.
"""

from dataclasses import dataclass
from itertools import product
from typing import Iterable, Mapping


# The order matches Character.direction and Character.movement_cell.
DIRECTIONS: tuple[str, ...] = ("right", "down", "left", "up")
DELTAS: Mapping[str, tuple[int, int]] = {
    "right": (1, 0),
    "down": (0, 1),
    "left": (-1, 0),
    "up": (0, -1),
}


@dataclass(frozen=True)
class GhostState:
    position: tuple[int, int]
    vulnerable: bool = False
    active: bool = True


@dataclass(frozen=True)
class SimulationState:
    """The search state: position, targets, and adversarial ghost positions."""

    pacman: tuple[int, int]
    ghosts: tuple[GhostState, ...]
    walkable: tuple[tuple[bool, ...], ...]
    pellets: frozenset[tuple[int, int]] = frozenset()
    energizers: frozenset[tuple[int, int]] = frozenset()
    initial_target_count: int = 0
    collected_targets: int = 0
    score: int = 0
    movement: tuple[tuple[tuple[bool, ...], ...], ...] = ()

    @property
    def width(self) -> int:
        return len(self.walkable[0]) if self.walkable else 0

    @property
    def height(self) -> int:
        return len(self.walkable)


def collision_map_to_walkable(collision_map: list[list[int]]) -> tuple[tuple[bool, ...], ...]:
    """Convert the game's four-bit movement map into a cell grid.

    A cell is considered walkable when it has at least one permitted movement.
    The individual movement permissions remain available through
    :func:`legal_actions`.
    """

    return tuple(tuple(bool(int(tile)) for tile in row) for row in collision_map)


def collision_map_to_movement(collision_map: list[list[int]]) -> tuple[tuple[tuple[bool, ...], ...], ...]:
    """Return per-cell movement flags in right/down/left/up order."""

    return tuple(
        tuple(_movement_flags(collision_map, (x, y)) for x in range(len(row)))
        for y, row in enumerate(collision_map)
    )


def _movement_flags(collision_map: list[list[int]], position: tuple[int, int]) -> tuple[bool, ...]:
    x, y = position
    if y < 0 or y >= len(collision_map) or x < 0 or x >= len(collision_map[y]):
        return (False, False, False, False)
    # This mirrors Character.movement_cell exactly: right, down, left, up.
    return tuple(bool(int(bit)) for bit in reversed(f"{collision_map[y][x]:04b}"))


def legal_actions(collision_map: list[list[int]], position: tuple[int, int]) -> tuple[str, ...]:
    """Return legal cardinal actions from a cell, including tunnel wrapping."""

    flags = _movement_flags(collision_map, position)
    actions = []
    width = len(collision_map[0]) if collision_map else 0
    height = len(collision_map)
    for index, (action, (dx, dy)) in enumerate(DELTAS.items()):
        if not flags[index]:
            continue
        nx, ny = position[0] + dx, position[1] + dy
        # The runtime wraps screen edges, so horizontal tunnels are legal.
        if width:
            nx %= width
        if 0 <= ny < height:
            actions.append(action)
    return tuple(actions)


def move_position(state: SimulationState, position: tuple[int, int], action: str) -> tuple[int, int]:
    dx, dy = DELTAS[action]
    x = position[0] + dx
    y = position[1] + dy
    if state.width:
        x %= state.width
    return x, y


def ghost_action_combinations(
    state: SimulationState, *, max_combinations: int = 64
) -> tuple[tuple[str, ...], ...]:
    """Build bounded joint ghost moves for the minimizing player.

    Four ghosts can create 4^4 combinations at a junction.  The cap keeps the
    real-time agent predictable while still considering all normal branches.
    """

    choices: list[tuple[str, ...]] = []
    for ghost in state.ghosts:
        if not ghost.active:
            choices.append(("none",))
            continue
        actions = legal_actions_from_state(state, ghost.position)
        choices.append(actions or ("none",))
    combinations = tuple(product(*choices))
    return combinations[:max_combinations]


def legal_actions_from_state(state: SimulationState, position: tuple[int, int]) -> tuple[str, ...]:
    """Return legal moves using exact map permissions when available."""

    result = []
    flags = state.movement[position[1]][position[0]] if state.movement else None
    for index, (action, (dx, dy)) in enumerate(DELTAS.items()):
        x = position[0] + dx
        y = position[1] + dy
        if state.width:
            x %= state.width
        if 0 <= y < state.height and (flags[index] if flags else state.walkable[y][x]):
            result.append(action)
    return tuple(result)


def apply_pacman_action(state: SimulationState, action: str) -> SimulationState:
    position = move_position(state, state.pacman, action)
    pellets = state.pellets - {position}
    energizers = state.energizers - {position}
    collected_pellet = position in state.pellets
    collected_energizer = position in state.energizers
    collected = state.collected_targets + int(collected_pellet or collected_energizer)
    score = state.score + (50 if collected_energizer else 10 if collected_pellet else 0)
    return SimulationState(
        pacman=position,
        ghosts=state.ghosts,
        walkable=state.walkable,
        pellets=frozenset(pellets),
        energizers=frozenset(energizers),
        initial_target_count=state.initial_target_count,
        collected_targets=collected,
        score=score,
        movement=state.movement,
    )


def apply_ghost_actions(state: SimulationState, actions: Iterable[str]) -> SimulationState:
    ghosts = []
    for ghost, action in zip(state.ghosts, actions):
        if action == "none" or not ghost.active:
            ghosts.append(ghost)
            continue
        ghosts.append(GhostState(move_position(state, ghost.position, action), ghost.vulnerable, ghost.active))
    return SimulationState(
        pacman=state.pacman,
        ghosts=tuple(ghosts),
        walkable=state.walkable,
        pellets=state.pellets,
        energizers=state.energizers,
        initial_target_count=state.initial_target_count,
        collected_targets=state.collected_targets,
        score=state.score,
        movement=state.movement,
    )


def extract_state(pacman, ghosts, loader, seeds=None) -> SimulationState:
    """Extract a search state from the existing game objects."""

    pellets = frozenset(seeds.remaining_positions) if seeds is not None else frozenset()
    energizers = frozenset(seeds.energizer_positions) if seeds is not None else frozenset()
    snapshots = tuple(
        GhostState(
            position=ghost.get_cell(),
            vulnerable=getattr(getattr(ghost, "state", None), "name", "") == "FRIGHTENED",
            active=getattr(getattr(ghost, "state", None), "name", "") not in {"HIDDEN", "EATEN", "INDOOR"},
        )
        for ghost in ghosts
    )
    return SimulationState(
        pacman=pacman.get_cell(),
        ghosts=snapshots,
        walkable=collision_map_to_walkable(loader.collision_map),
        pellets=pellets,
        energizers=energizers,
        initial_target_count=len(pellets) + len(energizers),
        collected_targets=0,
        score=0,
        movement=collision_map_to_movement(loader.collision_map),
    )
