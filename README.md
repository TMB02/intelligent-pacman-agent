# Pacman
[![ci-status](https://github.com/BaggerFast/Pacman/workflows/CI/badge.svg)](https://github.com/BaggerFast/Pacman/actions/)
[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/BaggerFast/Pacman/main.svg)](https://results.pre-commit.ci/latest/github/BaggerFast/Pacman/main)
[![CodeFactor](https://www.codefactor.io/repository/github/baggerfast/pacman/badge)](https://www.codefactor.io/repository/github/baggerfast/pacman)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)

Pacman is a simple game written on Pygame. The game was created as a learning project to explore
the possibilities of Pygame and develop game applications.

## 📺 Preview
https://github.com/BaggerFast/Pacman/assets/54527361/415e3585-086f-4111-822f-5049471ccbd8

Watch  full video on [YouTube](https://www.youtube.com/watch?v=VpNoZ70wDEg)

## 💻 Tech Stack
- [Python 3.10](https://www.python.org/)
- [Pygame](https://www.pygame.org/news)
- **Tools:**
  - [Black](https://github.com/psf/black)
  - [Isort](https://github.com/PyCQA/isort)
  - [PyLint](https://github.com/pylint-dev/pylint)
  - [CodeFactor](https://www.codefactor.io/)
    
## 👀 Look at this
- [Text](pacman/objects/text.py)
- [Button + controller](pacman/objects/buttons)
- [Sounds + controller](pacman/sound)
- [Scenes + SceneManager](pacman/scenes)
- [Animators + SpriteSheets](pacman/animator)
- [Saves - json serialize/deserialize](pacman/storage)

## 💾 Cheat codes
- In Game
  - **god** - victory scene
  - **kill** - lose scene
  - **aezakmi** - give 1 extra live
- In Menu
  - **pycman** - unlock all skins and levels

## Intelligent AI mode

The project includes a separate `pacman/ai/` layer with:

- immutable cell-based simulation states;
- Minimax with Pac-Man as MAX and ghosts as MIN;
- Alpha-Beta pruning with node/pruning/time metrics;
- explainable evaluation using score rewards, target progress, nearest targets,
  mobility, escape routes, non-linear near-ghost threat, collision risk,
  vulnerable-ghost opportunities, and energizer strategy;
- bounded joint ghost responses so decisions remain suitable for real-time play.

Human gameplay remains the default. Run the integrated intelligent agent with:

```bash
PACMAN_AI_MODE=intelligent PACMAN_AI_DEPTH=2 python3 run.py
```

The live controller uses a risk-aware corridor route, proactive energizer
seeking, threat-focused ghost responses, a one-step collision shield, and an
emergency escape policy. Depth 3 is available for offline experiments but is
not recommended for live play because four-ghost search becomes too slow.
Ghost movement uses the original game rules again: normal chase/scatter speed,
slow-zone reduction, frightened movement, and eaten-ghost return speed are
preserved. After an energizer, vulnerable ghosts become explicit AI targets;
the simulation models eating them and awards 200, 400, 800, and 1600 points
for consecutive ghost captures.
The original renderer, collision system, ghost runtime behavior, scoring,
lives, and win/lose flow are retained; the AI supplies Pac-Man's next desired
direction at cell centers.

### Syllabus mapping

- **Unit II — State-space search:** immutable maze states, legal actions,
  corridor BFS route distances, and heuristic evaluation.
- **Unit III — Adversarial search and game theory:** Pac-Man is the MAX player,
  ghosts are the MIN player, and Alpha-Beta pruning reduces the search tree.
- **Game-theory limitation:** the ghosts are simulated as bounded adversarial
  responses, while the runtime ghosts remain deterministic chase/scatter
  agents. Correct speed and frightened-ghost rules improve fidelity but do not
  by themselves constitute a mathematical guarantee of winning every level.

Run the AI unit tests with:

```bash
python3 -m unittest discover -s tests -v
```

For the complete-win presentation recording, use the explicit showcase
condition. Alpha-Beta still selects every Pac-Man action and all pellets are
collected from the real level; ghost damage is disabled only to isolate and
demonstrate navigation/coverage completion:

```bash
PACMAN_AI_MODE=intelligent PACMAN_AI_SHOWCASE=1 python3 scripts/record_ai_session.py
```

The recording overlay labels this as `SHOWCASE: NO DAMAGE`; it is not the
normal competitive game mode.

## 🎧 Set custom sounds in FUN MODE
![img.png](assets/fun_mode.png)

## 🚑 Support 
Please click the `star` button, if this game was helpful to you.
