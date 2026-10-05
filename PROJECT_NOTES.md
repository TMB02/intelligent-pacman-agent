# Intelligent Pac-Man Agent — Project Notes

## Base game

This project starts from [BaggerFast/Pacman](https://github.com/BaggerFast/Pacman), a Pygame Pac-Man game released under the MIT License.

The upstream game is retained as the environment: maze, sprites, scenes, levels, sounds, scoring, lives, and win/lose flow. The upstream `LICENSE.txt` and copyright notice are intentionally preserved.

## Planned AI contribution

The college AI laboratory extension will be implemented as a separate `ai/` layer so the original game remains identifiable and reusable:

- formal game-state extraction;
- target selection with explainable utility scores;
- A* pathfinding implemented from scratch;
- ghost danger evaluation;
- lightweight Minimax simulation;
- Alpha-Beta pruning and performance metrics;
- human, A* AI, and intelligent AI modes;
- optional path/debug/explanation panel;
- reproducible performance comparisons based on actual runs.

The current commit is the clean, runnable game foundation. AI integration should be added in incremental commits with tests and attribution kept separate from upstream code.

## Run

```bash
python3 -m pip install -r requirements.txt
python3 run.py
```
