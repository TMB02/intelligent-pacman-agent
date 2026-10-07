# Intelligent Pac-Man: Failure Analysis and Improvements

## Executive summary

The first intelligent-agent version was a **short-horizon Alpha-Beta controller**. It could choose legal pellet-seeking moves, but it was not a complete Pac-Man solver. Ghosts sometimes trapped Pac-Man in a corridor before the next search decision, so a locally attractive pellet outweighed a future collision.

The updated controller is substantially safer, but the current evidence does **not** justify claiming a guaranteed win on all ten levels. That claim would be misleading without a longer all-level completion run. The correct presentation statement is:

> “We improved the agent from local pellet-seeking to risk-aware corridor planning with Alpha-Beta pruning, proactive energizer use, and emergency escape logic. It is faster and survives longer, but guaranteed completion against stochastic ghosts remains a future milestone.”

## What failed originally

### 1. Manhattan distance ignored walls

The evaluator attracted Pac-Man toward the nearest target using Manhattan distance. A pellet could look close even when the maze required a long detour. This encouraged turns into corridors that were strategically unsafe.

### 2. The adversarial ghost branch was truncated incorrectly

Four ghosts can create many joint responses. The old bounded search kept the first combinations produced by `itertools.product`. Product order is not threat order, so a dangerous response from a later ghost could be omitted from the search.

### 3. The search horizon did not match the game timing

The AI chooses at cell centers, while the live characters move one pixel per frame. A depth-2 search sees only a short tactical window. At the first diagnosis, Pac-Man reached a tunnel with ghosts on both sides; both immediately available directions were already lethal.

### 4. No one-step safety shield existed

The original controller trusted the heuristic value. It did not explicitly reject a legal action whose worst bounded ghost response entered a collision range.

### 5. Depth 3 was not a practical live fix

An offline depth-3 smoke test visited about 33,410 nodes and took about 2 seconds for one decision. Increasing depth alone would make the agent unresponsive rather than reliable.

## What was implemented

### Syllabus alignment

The project uses algorithms from the supplied syllabus image:

- **Unit II — Problem solving:** state-space search, legal-action generation,
  corridor BFS distances, and heuristic evaluation;
- **Unit III — Adversarial search and game theory:** Minimax with Pac-Man as
  MAX, ghosts as MIN, and Alpha-Beta pruning.

This is a stronger academic choice than presenting the game as only a
game-specific heuristic. The state, actions, utility function, MAX/MIN turns,
and pruning metrics can all be explained in viva.

### Equal-speed experiment

The runtime ghosts now match Pac-Man's speed in the demonstration mode. Each
ghost performs exactly one movement step per frame, which is the same movement
step used by Pac-Man. The original slow-zone, frightened-mode, and eaten-ghost
speed modifiers are disabled so the live environment matches the fair-speed
assumption.

Equal speed makes the experiment fair and can improve completion probability,
but it does not mathematically guarantee a win: ghosts still chase, Pac-Man
still has a finite search horizon, and the maze contains unavoidable tactical
situations. We therefore report completion results from repeatable runs rather
than claiming a guarantee without evidence.

### Score-aware simulation state

`SimulationState` now tracks:

- normal pellets and energizers separately;
- collected target count;
- score proxy: 10 points per pellet and 50 per energizer;
- exact directional movement permissions from the level collision map.

### Threat-focused ghost responses

Each active ghost contributes its two most threatening legal moves. The joint responses are ranked by the resulting distance to Pac-Man rather than being truncated arbitrarily. This keeps the branch count suitable for real-time play while retaining the dangerous chase alternatives.

### Maze-aware target distance

The evaluator uses a cached corridor BFS for reachable targets rather than relying only on Manhattan distance. This prevents the heuristic from preferring targets through walls.

### Non-linear danger evaluation

The new evaluation function includes:

- strong terminal collision penalty;
- quadratic penalties for nearby dangerous ghosts;
- escape-route and dead-end terms;
- larger rewards for vulnerable-ghost opportunities;
- energizer strategy when dangerous ghosts are active;
- explicit corridor-trap penalty;
- score and target-progress rewards.

### Risk-aware route planning

A global BFS route planner guides Pac-Man toward reachable targets while avoiding cells within a danger envelope. When active ghosts exist and energizers remain, the planner prioritizes power pellets so Pac-Man can switch the game into frightened mode.

### Safety and emergency behavior

Before scoring actions, the controller:

1. rejects actions with an immediate lethal ghost response when a safe legal action exists;
2. enters hard escape mode when a dangerous ghost is close;
3. rewards actions that increase distance from the nearest dangerous ghost;
4. uses a wider ghost danger envelope for route planning than the collision test itself.

## Validation evidence

### Automated tests

The AI test suite passes **9 tests**, including:

- legal action ordering;
- pellet collection and score accounting;
- higher energizer reward;
- immediate ghost avoidance;
- distant-vs-near ghost evaluation;
- energizer risk compensation;
- Alpha-Beta decision equivalence and pruning behavior.
- threat-prioritized ghost response ordering;
- rejection of a move with a lethal immediate ghost response.

### Headless real-game sweep before equal-speed mode

A 1,200-frame headless sweep was run against all ten real map files with depth 2. This is a survival-window test, not a full level-completion test.

| Level | Result in latest sweep |
|---|---|
| 1 | Death at frame 1119 |
| 2 | Survived 1200-frame window |
| 3 | Death at frame 289 |
| 4 | Death at frame 526 |
| 5 | Death at frame 485 |
| 6 | Death at frame 502 |
| 7 | Death at frame 459 |
| 8 | Survived 1200-frame window |
| 9 | Death at frame 254 |
| 10 | Death at frame 291 |

The sweep demonstrates that the agent is still not a guaranteed all-level winner. It does, however, provide a repeatable baseline and prevents us from claiming success based only on a short video clip.

### Equal-speed sweep

After enabling `MATCH_PACMAN_SPEED`, the same 1,200-frame experiment produced:

| Level | Equal-speed result |
|---|---|
| 1 | Survived 1200-frame window |
| 2 | Survived 1200-frame window |
| 3 | Death at frame 289 |
| 4 | Death at frame 526 |
| 5 | Survived 1200-frame window |
| 6 | Death at frame 403 |
| 7 | Death at frame 474 |
| 8 | Survived 1200-frame window |
| 9 | Death at frame 254 |
| 10 | Death at frame 253 |

This is evidence that equalizing speed changes the experimental condition and
improves some runs, but it is not sufficient for an all-level guarantee. The
remaining failures are planning-horizon and route-coverage failures, not a
ghost-speed mismatch.

## How to explain the architecture

```text
Live Pygame objects
        |
        v
Immutable SimulationState
  - Pac-Man cell
  - ghost cells and states
  - collision permissions
  - remaining targets
        |
        +--> risk-aware route planner
        |
        +--> Alpha-Beta search
                MAX: Pac-Man action
                MIN: threat-focused ghost responses
                evaluator: score + route + survival
        |
        v
Safety shield / emergency escape
        |
        v
Pac-Man desired direction at the next cell center
```

### Short presentation script

1. **“The original problem was not that Minimax was absent; it was that the state and heuristic were incomplete.”**
2. **“Manhattan distance could recommend a pellet through a wall, and arbitrary branch truncation could hide a dangerous ghost response.”**
3. **“We added exact maze routes, score-aware rewards, threat-focused ghost branches, energizer strategy, a collision shield, and emergency escape behavior.”**
4. **“Depth 3 is theoretically stronger but too slow for live play, so both the reusable agent and integrated controller default to depth 2.”**
5. **“The tests pass and survival improves, but stochastic ghosts and the short action horizon mean we cannot honestly claim guaranteed completion on all levels yet.”**

## Next milestone for guaranteed completion

To make “win all levels” a valid claim, the next version should add at least one of:

- ghost velocity and target mode to the state, not only ghost position;
- a multi-step reachable-set safety planner for the full interval between cell centers;
- a persistent coverage planner that records visited junctions and avoids loops;
- episode-based evaluation across every level and difficulty;
- a learned policy trained against randomized ghost behavior, with the current Alpha-Beta controller retained as a safety fallback.

The current implementation is therefore a stronger and more explainable research baseline, not a mathematically guaranteed Pac-Man solver.
