"""Record a headless intelligent Pac-Man session as a visual demonstration."""

import os
import subprocess
import sys
from pathlib import Path

# The recorder renders frames without requiring a desktop display or speakers.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ["PACMAN_AI_MODE"] = "intelligent"
os.environ.setdefault("PACMAN_AI_DEPTH", "2")

import pygame

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pacman.data_core import Cfg, Colors, FontCfg
from pacman.data_core.enums import GameStateEnum
from pacman.scenes import SceneManager
from pacman.scenes.main_scene import MainScene


FPS = Cfg.FPS
DURATION_SECONDS = 12
GAME_SIZE = (Cfg.RESOLUTION.WIDTH, Cfg.RESOLUTION.HEIGHT)
PANEL_WIDTH = 320
FRAME_SIZE = (GAME_SIZE[0] + PANEL_WIDTH, GAME_SIZE[1] + GAME_SIZE[1] % 2)
OUTPUT = Path(__file__).resolve().parents[1] / "artifacts" / "intelligent-pacman-session.mp4"


def draw_panel(canvas: pygame.Surface, scene: MainScene, font: pygame.font.Font) -> None:
    panel_x = GAME_SIZE[0]
    pygame.draw.rect(canvas, (12, 12, 20), (panel_x, 0, PANEL_WIDTH, GAME_SIZE[1]))
    pygame.draw.line(canvas, Colors.BLUE, (panel_x, 0), (panel_x, GAME_SIZE[1]), 2)

    agent = scene._MainScene__ai_agent
    metrics = agent.metrics
    values = agent.action_values
    action = max(values, key=values.get) if values else "waiting"
    mode = os.environ.get("PACMAN_AI_MODE", "intelligent").upper()

    lines = [
        ("INTELLIGENT PAC-MAN", Colors.YELLOW),
        ("", Colors.WHITE),
        (f"MODE: {mode}", Colors.WHITE),
            ("ALGORITHM:", Colors.WHITE),
            ("MINIMAX + ALPHA-BETA", Colors.GREEN),
            (f"DEPTH: {agent.search.depth}", Colors.WHITE),
            ("GHOST SPEED: PAC-MAN", Colors.GREEN),
        ("", Colors.WHITE),
        (f"SELECTED ACTION: {action.upper()}", Colors.YELLOW),
        ("ACTION VALUES", Colors.WHITE),
    ]
    for direction in ("right", "down", "left", "up"):
        lines.append((f"  {direction.upper():5} {values.get(direction, 0):7.1f}", Colors.GREEN if direction == action else Colors.WHITE))
    lines.extend(
        [
            ("", Colors.WHITE),
            (f"NODES VISITED: {metrics.nodes_visited}", Colors.WHITE),
            (f"NODES PRUNED:  {metrics.nodes_pruned}", Colors.GREEN),
            (f"DECISION:      {metrics.decision_time_ms:.2f} ms", Colors.WHITE),
            ("", Colors.WHITE),
            ("Pac-Man is controlled", Colors.GRAY),
            ("automatically by the", Colors.GRAY),
            ("Alpha-Beta agent.", Colors.GRAY),
        ]
    )

    y = 12
    for text, color in lines:
        if text:
            canvas.blit(font.render(text, True, color), (panel_x + 14, y))
        y += 13


def main() -> int:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    pygame.init()
    pygame.display.set_mode((1, 1))
    scene = MainScene()
    SceneManager().reset(scene)
    scene._MainScene__state = GameStateEnum.ACTION

    command = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-vcodec",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{FRAME_SIZE[0]}x{FRAME_SIZE[1]}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        str(OUTPUT),
    ]
    encoder = subprocess.Popen(command, stdin=subprocess.PIPE)
    font = pygame.font.Font(FontCfg.DEFAULT, 10)
    canvas = pygame.Surface(FRAME_SIZE)

    try:
        for _ in range(FPS * DURATION_SECONDS):
            scene.process_logic()
            game_surface = scene.draw()
            canvas.fill((0, 0, 0))
            canvas.blit(game_surface, (0, 0))
            draw_panel(canvas, scene, font)
            try:
                encoder.stdin.write(pygame.image.tostring(canvas, "RGB"))
            except BrokenPipeError as error:
                raise RuntimeError("ffmpeg stopped before the recording completed") from error
    finally:
        encoder.stdin.close()
        return_code = encoder.wait()
        pygame.quit()

    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with code {return_code}")
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
