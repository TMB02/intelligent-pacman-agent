"""Benchmark the intelligent agent across all bundled Pac-Man levels.

The benchmark uses each level's real collision map, spawn coordinates, pellets,
and energizers. It measures repeated search decisions from evolving immutable
states and writes both raw CSV data and a publication-ready PNG chart.
"""

from __future__ import annotations

import csv
import json
import os
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import matplotlib.pyplot as plt
import numpy as np

from pacman.ai import AlphaBetaAgent
from pacman.ai.state import (
    GhostState,
    SimulationState,
    apply_ghost_actions,
    apply_pacman_action,
    collision_map_to_movement,
    collision_map_to_walkable,
    ghost_action_combinations,
)


SAMPLES = int(os.getenv("PACMAN_AI_BENCH_SAMPLES", "12"))
DEPTH = int(os.getenv("PACMAN_AI_BENCH_DEPTH", "2"))
OUT_DIR = ROOT / "artifacts"
CSV_PATH = OUT_DIR / "ai-level-performance.csv"
PNG_PATH = OUT_DIR / "ai-level-performance.png"
GHOST_NAMES = ("inky", "pinky", "clyde", "blinky")


def spawn_cell(position: list[float | int]) -> tuple[int, int]:
    """Match CellUtil.get_cell after Character creates a centered spawn rect."""

    return int(position[0] + 0.5), int(position[1])


def build_targets(data: dict) -> tuple[frozenset[tuple[int, int]], frozenset[tuple[int, int]]]:
    """Mirror SeedLoader's removal rules for an exact level target set."""

    seeds = [[bool(value) for value in row] for row in data["collision_map"]]
    fruit_x, fruit_y = data["static_objects"]["fruit"]
    seeds[fruit_y][int(fruit_x - 0.5)] = False
    seeds[fruit_y][int(fruit_x + 0.5)] = False

    pacman_x, pacman_y = data["characters"]["pacman"]
    seeds[pacman_y][int(pacman_x - 0.5)] = False
    seeds[pacman_y][int(pacman_x + 0.5)] = False

    for rect in data["rects"]["no_dots"]:
        for y in range(rect[1], rect[3] + 1):
            for x in range(rect[0], rect[2] + 1):
                seeds[y][x] = False

    energizers = frozenset((int(x), int(y)) for x, y in data["static_objects"]["big_dots"])
    for x, y in energizers:
        seeds[y][x] = False
    pellets = frozenset((x, y) for y, row in enumerate(seeds) for x, present in enumerate(row) if present)
    return pellets, energizers


def build_state(data: dict) -> SimulationState:
    collision_map = data["collision_map"]
    pellets, energizers = build_targets(data)
    characters = data["characters"]
    ghosts = tuple(GhostState(spawn_cell(characters[name])) for name in GHOST_NAMES)
    return SimulationState(
        pacman=spawn_cell(characters["pacman"]),
        ghosts=ghosts,
        walkable=collision_map_to_walkable(collision_map),
        pellets=pellets,
        energizers=energizers,
        initial_target_count=len(pellets) + len(energizers),
        movement=collision_map_to_movement(collision_map),
    )


def benchmark_level(path: Path) -> dict[str, float | int | str]:
    data = json.loads(path.read_text())
    state = build_state(data)
    agent = AlphaBetaAgent(depth=DEPTH)
    times: list[float] = []
    visited: list[int] = []
    pruned: list[int] = []
    actions: list[str] = []

    for _ in range(SAMPLES):
        action = agent.choose_action(state)
        times.append(agent.last_metrics.decision_time_ms)
        visited.append(agent.last_metrics.nodes_visited)
        pruned.append(agent.last_metrics.nodes_pruned)
        actions.append(action)

        if action != "none":
            state = apply_pacman_action(state, action)
        responses = ghost_action_combinations(state, max_combinations=1)
        if responses:
            state = apply_ghost_actions(state, responses[0])

    total_nodes = sum(visited) + sum(pruned)
    return {
        "level": path.stem,
        "depth": DEPTH,
        "samples": SAMPLES,
        "mean_decision_ms": mean(times),
        "p95_decision_ms": float(np.percentile(times, 95)),
        "mean_nodes_visited": mean(visited),
        "mean_nodes_pruned": mean(pruned),
        "pruning_efficiency_pct": (sum(pruned) / total_nodes * 100) if total_nodes else 0.0,
        "unique_actions": ",".join(sorted(set(actions))),
    }


def write_csv(rows: list[dict[str, float | int | str]]) -> None:
    fieldnames = list(rows[0].keys())
    with CSV_PATH.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_chart(rows: list[dict[str, float | int | str]]) -> None:
    levels = [f"L{int(row['level']) + 1}" for row in rows]
    mean_times = [float(row["mean_decision_ms"]) for row in rows]
    p95_times = [float(row["p95_decision_ms"]) for row in rows]
    efficiencies = [float(row["pruning_efficiency_pct"]) for row in rows]
    nodes_pruned = [float(row["mean_nodes_pruned"]) for row in rows]
    x = np.arange(len(levels))

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, (time_axis, prune_axis) = plt.subplots(1, 2, figsize=(14, 6), dpi=160)
    fig.patch.set_facecolor("#f6f8fb")
    fig.suptitle(
        f"Intelligent Pac-Man Performance Across Levels\nAlpha-Beta depth {DEPTH} · {SAMPLES} decisions per level",
        fontsize=16,
        fontweight="bold",
        color="#172033",
    )

    bars = time_axis.bar(x, mean_times, color="#2f6fed", alpha=0.9, label="Mean decision time")
    time_axis.plot(x, p95_times, color="#e45756", marker="o", linewidth=2, label="P95 decision time")
    time_axis.set_title("Decision latency", fontweight="bold")
    time_axis.set_ylabel("Milliseconds")
    time_axis.set_xlabel("Game level")
    time_axis.set_xticks(x, levels)
    time_axis.legend(frameon=True)
    time_axis.set_ylim(bottom=0)
    for bar, value in zip(bars, mean_times):
        time_axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.1f}",
            ha="center",
            va="bottom",
            fontsize=8,
        )

    prune_bars = prune_axis.bar(x, efficiencies, color="#19a974", alpha=0.9, label="Pruning efficiency")
    prune_axis.set_title("Alpha-Beta pruning efficiency", fontweight="bold")
    prune_axis.set_ylabel("Pruned / (visited + pruned) (%)")
    prune_axis.set_xlabel("Game level")
    prune_axis.set_xticks(x, levels)
    prune_axis.set_ylim(0, max(10, max(efficiencies) * 1.25))
    prune_axis.legend(frameon=True, loc="upper right")
    for bar, efficiency, count in zip(prune_bars, efficiencies, nodes_pruned):
        prune_axis.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{efficiency:.1f}%\n({count:.1f} events)",
            ha="center",
            va="bottom",
            fontsize=7,
        )

    fig.text(
        0.5,
        0.01,
        "Measured from real bundled map layouts and spawn states; lower latency and "
        "higher pruning efficiency are preferable.",
        ha="center",
        fontsize=9,
        color="#4c566a",
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.91))
    fig.savefig(PNG_PATH, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    map_paths = sorted(
        (ROOT / "assets" / "maps").glob("*.json"),
        key=lambda item: int(item.stem),
    )
    rows = [benchmark_level(path) for path in map_paths]
    write_csv(rows)
    write_chart(rows)
    print(f"Wrote {CSV_PATH}")
    print(f"Wrote {PNG_PATH}")
    for row in rows:
        print(
            f"Level {int(row['level']) + 1}: "
            f"mean={float(row['mean_decision_ms']):.3f} ms, "
            f"p95={float(row['p95_decision_ms']):.3f} ms, "
            f"pruning={float(row['pruning_efficiency_pct']):.2f}%"
        )


if __name__ == "__main__":
    main()
