# Intelligent Pac-Man Agent — Project Notes

## Base game

This project starts from [BaggerFast/Pacman](https://github.com/BaggerFast/Pacman), a Pygame Pac-Man game released under the MIT License.

The upstream game is retained as the environment: maze, sprites, scenes, levels, sounds, scoring, lives, and win/lose flow. The upstream `LICENSE.txt` and copyright notice are intentionally preserved.

## AI contribution

The college AI laboratory extension is implemented as a separate `pacman/ai/` layer so the original game remains identifiable and reusable:

- formal game-state extraction;
- target selection with explainable utility scores;
- A* pathfinding implemented from scratch;
- ghost danger evaluation;
- lightweight Minimax simulation;
- Alpha-Beta pruning and performance metrics;
- human, A* AI, and intelligent AI modes;
- optional path/debug/explanation panel;
- reproducible performance comparisons based on actual runs.

Minimax and Alpha-Beta search now run on immutable simulation states. The live
game can opt into the integrated intelligent agent with `PACMAN_AI_MODE=intelligent`.
The default human mode remains unchanged. AI tests are in `tests/test_ai.py`.

## Run

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```
