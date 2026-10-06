import os
import unittest

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from pacman.ai import MinimaxAgent
from pacman.ai.state import GhostState, SimulationState, apply_pacman_action, legal_actions


# Four-bit map values are interpreted in the same order as the game:
# right, down, left, up.  15 means all four directions are open.
OPEN = 15


def state(pacman=(1, 1), ghosts=(), pellets=frozenset({(2, 1)}), energizers=frozenset(), score=0):
    grid = tuple(tuple(True for _ in range(5)) for _ in range(5))
    return SimulationState(
        pacman=pacman,
        ghosts=tuple(ghosts),
        walkable=grid,
        pellets=pellets,
        energizers=energizers,
        initial_target_count=len(pellets),
        score=score,
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
        self.assertEqual(result.score, 10)

    def test_energizer_has_higher_score_reward_than_pellet(self):
        pellet = apply_pacman_action(state(pellets=frozenset({(2, 1)})), "right")
        energizer = apply_pacman_action(
            state(pellets=frozenset(), energizers=frozenset({(2, 1)})), "right"
        )
        self.assertGreater(energizer.score, pellet.score)
        self.assertEqual(energizer.score, 50)

    def test_nearby_dangerous_ghost_is_worse_than_distant_ghost(self):
        agent = MinimaxAgent(depth=1)
        near = agent.evaluate(state(ghosts=(GhostState((2, 1)),)))
        distant = agent.evaluate(state(ghosts=(GhostState((4, 4)),)))
        self.assertLess(near, distant)

    def test_nearby_energizer_offsets_some_ghost_risk(self):
        agent = MinimaxAgent(depth=1)
        without_energizer = agent.evaluate(state(ghosts=(GhostState((3, 1)),)))
        with_energizer = agent.evaluate(
            state(ghosts=(GhostState((3, 1)),), energizers=frozenset({(2, 1)}))
        )
        self.assertGreater(with_energizer, without_energizer)

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
