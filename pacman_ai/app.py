"""Pygame application loop and user interaction."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
import sys
from time import monotonic

import pygame

from .audio import SoundBank
from .algorithms import manhattan
from .models import Algorithm
from .planner import plan_route
from .session import GameSession
from .settings import (
    FPS,
    GHOST_STEP_SECONDS,
    PLAYER_STEP_SECONDS,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
)
from .ui import UIRenderer


class Scene(str, Enum):
    MENU = "menu"
    GAME = "game"


class PacmanApplication:
    """Interactive controller for the complete demo."""

    def __init__(self) -> None:
        pygame.mixer.pre_init(44_100, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("Optimized Pac-Man AI")
        try:
            self.screen = pygame.display.set_mode(
                (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SCALED | pygame.RESIZABLE
            )
        except pygame.error:
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

        project_root = Path(__file__).resolve().parents[1]
        self.session = GameSession(project_root / "maps")
        self.renderer = UIRenderer(self.screen)
        self.sounds = SoundBank()
        self.scene = Scene.MENU
        self.modal: str | None = None
        self.clock = pygame.time.Clock()
        self.active = True
        self.last_player_step = monotonic()
        self.last_ghost_step = monotonic()
        self._last_event_serial = self.session.event_serial

    def run(self) -> None:
        while self.active:
            delta = self.clock.tick(FPS) / 1000.0
            now = monotonic()
            self._handle_events()
            self._update(now)
            self._draw(now, delta)
            pygame.display.flip()
        pygame.quit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.active = False
            elif event.type == pygame.KEYDOWN:
                self._handle_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                action = self.renderer.action_at(event.pos)
                if action:
                    self._handle_action(action)

    def _handle_key(self, key: int) -> None:
        if self.modal is not None:
            if self.modal == "end":
                if key in {pygame.K_RETURN, pygame.K_r}:
                    self.modal = None
                    self.session.reset()
                elif key == pygame.K_ESCAPE:
                    self.modal = None
                    self.scene = Scene.MENU
                    self.session.running = False
                return
            if key in {pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_h}:
                self.modal = None
            return

        if self.scene == Scene.MENU:
            if key in {pygame.K_RETURN, pygame.K_SPACE}:
                self.scene = Scene.GAME
            elif key == pygame.K_ESCAPE:
                self.active = False
            return

        key_algorithms = {
            pygame.K_1: Algorithm.BFS,
            pygame.K_2: Algorithm.DFS,
            pygame.K_3: Algorithm.UCS,
            pygame.K_4: Algorithm.DIJKSTRA,
            pygame.K_5: Algorithm.A_STAR,
        }
        if key in key_algorithms:
            self.session.set_algorithm(key_algorithms[key])
        elif key == pygame.K_RETURN:
            self.session.toggle_running()
        elif key == pygame.K_SPACE:
            self.session.toggle_pause()
        elif key == pygame.K_s:
            self.session.step_player()
        elif key == pygame.K_c:
            self.session.compare_current_problem()
            self.modal = "compare"
        elif key == pygame.K_r:
            self.session.reset()
        elif key == pygame.K_m:
            self.session.next_map()
        elif key == pygame.K_g:
            self.session.toggle_dynamic_ghosts()
        elif key == pygame.K_h:
            self.modal = "help"
        elif key == pygame.K_ESCAPE:
            self.scene = Scene.MENU
            self.session.running = False

    def _handle_action(self, action: str) -> None:
        if action == "start":
            self.scene = Scene.GAME
        elif action == "close_modal":
            self.modal = None
        elif action == "menu":
            self.modal = None
            self.scene = Scene.MENU
            self.session.running = False
        elif action == "help":
            self.modal = "help"
        elif action == "toggle_run":
            self.session.toggle_running()
        elif action == "step":
            self.session.step_player()
        elif action == "compare":
            self.session.compare_current_problem()
            self.modal = "compare"
        elif action == "reset":
            self.modal = None
            self.session.reset()
        elif action == "next_map":
            self.session.next_map()
        elif action == "toggle_ghosts":
            self.session.toggle_dynamic_ghosts()
        elif action.startswith("algorithm:"):
            self.session.set_algorithm(Algorithm(action.split(":", 1)[1]))
        elif action.startswith("speed:"):
            self.session.set_speed(int(action.split(":", 1)[1]))

    def _update(self, now: float) -> None:
        if self.scene != Scene.GAME or self.modal is not None:
            return

        if self.session.running and not self.session.paused:
            if now - self.last_player_step >= PLAYER_STEP_SECONDS / self.session.speed:
                self.session.step_player(now)
                self.last_player_step = now
            if now - self.last_ghost_step >= GHOST_STEP_SECONDS / self.session.speed:
                self.session.step_ghosts(now)
                self.last_ghost_step = now

        if self.session.event_serial != self._last_event_serial:
            self._last_event_serial = self.session.event_serial
            self.sounds.play(self.session.last_event)

        if self.session.won or self.session.game_over:
            self.modal = "end"

    def _draw(self, now: float, delta: float) -> None:
        if self.scene == Scene.MENU:
            self.renderer.draw_menu(now)
            return
        self.renderer.draw_game(self.session, now, delta)
        if self.modal == "compare":
            self.renderer.draw_compare_modal(self.session, now)
        elif self.modal == "help":
            self.renderer.draw_help_modal()
        elif self.modal == "end":
            self.renderer.draw_end_modal(self.session)

    def save_preview(self, output_path: str | Path) -> Path:
        """Render a deterministic screenshot for documentation and QA."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.scene = Scene.GAME
        self.session.dynamic_ghosts = False
        targets = self.session.foods | self.session.power_foods
        target = max(targets, key=lambda item: manhattan(self.session.player, item))
        result = plan_route(
            self.session.algorithm,
            self.session.maze,
            self.session.player,
            target,
            self.session.ghost_positions,
        )
        self.session.target = target
        self.session.last_result = result
        self.session.route = result.path[1:]
        self.session.status = "Previewing a full A* route"
        self.renderer.explored_reveal = float(
            self.session.last_result.expanded_nodes if self.session.last_result else 0
        )
        self._draw(monotonic(), 1.0)
        pygame.display.flip()
        pygame.image.save(self.screen, path)
        return path

    def smoke_test(self, frames: int = 12) -> None:
        """Exercise startup, planning, update, and rendering without interaction."""

        self.scene = Scene.GAME
        self.session.dynamic_ghosts = False
        self.session.toggle_running()
        for _ in range(frames):
            now = monotonic()
            self.session.step_player(now)
            self._draw(now, 1 / FPS)
        pygame.display.flip()

    @staticmethod
    def shutdown() -> None:
        pygame.quit()


def abort_with_message(message: str) -> None:
    print(message, file=sys.stderr)
    pygame.quit()
    raise SystemExit(1)
