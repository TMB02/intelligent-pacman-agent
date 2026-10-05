import os
import unittest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from pacman.ai import MinimaxAgent
from pacman.ai.state import GhostState, SimulationState, apply_pacman_action, legal_actions


# Four-bit map values are interpreted in the same order as the game:
# right, down, left, up.  15 means all four directions are open.
OPEN = 15


def state(pacman=(1, 1), ghosts=(), pellets=frozenset({(2, 1)})):
    grid = tuple(tuple(True for _ in range(5)) for _ in range(5))
    return SimulationState(
        pacman=pacman,
        ghosts=tuple(ghosts),
        walkable=grid,
        pellets=pellets,
        initial_target_count=len(pellets),
    )


class AiTests(unittest.TestCase):
    def test_legal_actions_match_four_direction_order(self):
        collision_map = [[OPEN] * 3 for _ in range(3)]
        self.assertEqual(legal_actions(collision_map, (1, 1)), ("right", "down", "left", "up"))

    def test_pacman_collects_a_target_in_simulation(self):
        result = apply_pacman_action(state(), "right")
        self.assertEqual(result.pacman, (2, 1))
        self.assertNotIn((2, 1), result.pellets)
        self.assertEqual(result.collected_targets, 1)

    def test_minimax_avoids_an_immediate_ghost_collision(self):
        current = state(
            pacman=(1, 1),
            ghosts=(GhostState((2, 1)),),
            pellets=frozenset({(1, 2)}),
        )
        action = MinimaxAgent(depth=2).choose_action(current)
        self.assertNotEqual(action, "right")

    def test_alpha_beta_prunes_some_nodes(self):
        current = state(ghosts=(GhostState((4, 4)),), pellets=frozenset({(2, 1), (1, 2)}))
        plain = MinimaxAgent(depth=3, use_alpha_beta=False)
        pruned = MinimaxAgent(depth=3, use_alpha_beta=True)
        plain_action = plain.choose_action(current)
        pruned_action = pruned.choose_action(current)
        self.assertEqual(pruned_action, plain_action)
        self.assertLessEqual(pruned.last_metrics.nodes_visited, plain.last_metrics.nodes_visited)
        self.assertGreaterEqual(pruned.last_metrics.nodes_pruned, 0)


if __name__ == "__main__":
    unittest.main()
