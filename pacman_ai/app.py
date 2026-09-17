"""Pygame application loop and user interaction."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
import sys
from time import monotonic

import pygame

from .audio import SoundBank
from .algorithms import manhattan
from .editor import EditorTool, MapEditor
from .models import Algorithm, HeuristicMode
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
    EDITOR = "editor"


class PacmanApplication:
    """Interactive controller for the complete demo."""

    def __init__(self) -> None:
        pygame.mixer.pre_init(44_100, -16, 1, 512)
        pygame.init()
        pygame.display.set_caption("Adaptive Pac-Man AI — Pathfinding Laboratory")
        try:
            self.screen = pygame.display.set_mode(
                (WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SCALED | pygame.RESIZABLE
            )
        except pygame.error:
            self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))

        self.project_root = Path(__file__).resolve().parents[1]
        self.session = GameSession(self.project_root / "maps")
        self.renderer = UIRenderer(self.screen)
        self.sounds = SoundBank()
        self.scene = Scene.MENU
        self.modal: str | None = None
        self.clock = pygame.time.Clock()
        self.active = True
        self.last_player_step = monotonic()
        self.last_ghost_step = monotonic()
        self._last_event_serial = self.session.event_serial
        self.editor: MapEditor | None = None
        self.replay_index = 0
        self.replay_playing = False
        self.last_replay_step = monotonic()
        self.export_error = ""

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
                elif self.scene == Scene.EDITOR and self.editor is not None:
                    cell = self.renderer.editor_cell_at(event.pos, self.editor)
                    if cell is not None:
                        self.editor.apply(cell)

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
            if self.modal == "replay":
                if key == pygame.K_ESCAPE:
                    self.modal = None
                    self.replay_playing = False
                elif key == pygame.K_LEFT:
                    self.replay_index = max(0, self.replay_index - 1)
                elif key == pygame.K_RIGHT:
                    self.replay_index = min(
                        len(self.session.replay.frames) - 1,
                        self.replay_index + 1,
                    )
                elif key == pygame.K_SPACE:
                    self.replay_playing = not self.replay_playing
                elif key == pygame.K_s:
                    self.session.save_replay(self.project_root / "exports")
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

        if self.scene == Scene.EDITOR:
            if self.editor is None:
                self.scene = Scene.GAME
                return
            tool_keys = {
                pygame.K_1: EditorTool.FLOOR,
                pygame.K_2: EditorTool.WALL,
                pygame.K_3: EditorTool.START,
                pygame.K_4: EditorTool.EXIT,
                pygame.K_5: EditorTool.PELLET,
                pygame.K_6: EditorTool.POWER,
                pygame.K_7: EditorTool.GHOST,
                pygame.K_8: EditorTool.TERRAIN_2,
                pygame.K_9: EditorTool.TERRAIN_3,
            }
            if key in tool_keys:
                self.editor.set_tool(tool_keys[key])
            elif key == pygame.K_v:
                self.editor.validate()
            elif key == pygame.K_s:
                self._save_editor()
            elif key == pygame.K_ESCAPE:
                self.scene = Scene.GAME
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
        elif key == pygame.K_a:
            self.session.toggle_auto_mode()
        elif key == pygame.K_e:
            self.modal = "explain"
        elif key == pygame.K_x:
            self.session.run_research_experiment()
            self.modal = "experiment"
        elif key == pygame.K_j:
            self.session.compare_current_heuristics()
            self.modal = "heuristics"
        elif key == pygame.K_v:
            self._open_replay()
        elif key == pygame.K_f:
            self._open_editor()
        elif key == pygame.K_b:
            self._export_bundle()
        elif key == pygame.K_l:
            self.renderer.side_tab = "lab" if self.renderer.side_tab == "play" else "play"
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
        elif action == "toggle_ghost_ai":
            self.session.toggle_advanced_ghost_ai()
        elif action == "toggle_auto":
            self.session.toggle_auto_mode()
        elif action == "toggle_heatmap":
            self.session.toggle_heatmap()
        elif action == "experiment":
            self.session.run_research_experiment()
            self.modal = "experiment"
        elif action == "heuristic_compare":
            self.session.compare_current_heuristics()
            self.modal = "heuristics"
        elif action == "explain":
            self.modal = "explain"
        elif action == "replay":
            self._open_replay()
        elif action == "save_replay":
            self.session.save_replay(self.project_root / "exports")
            self.modal = "export"
        elif action == "export_bundle":
            self._export_bundle()
        elif action == "editor":
            self._open_editor()
        elif action == "editor_back":
            self.scene = Scene.GAME
        elif action == "editor_validate" and self.editor is not None:
            self.editor.validate()
        elif action == "editor_save":
            self._save_editor()
        elif action == "replay_prev":
            self.replay_index = max(0, self.replay_index - 1)
        elif action == "replay_next":
            self.replay_index = min(
                len(self.session.replay.frames) - 1,
                self.replay_index + 1,
            )
        elif action == "replay_toggle":
            self.replay_playing = not self.replay_playing
        elif action.startswith("tab:"):
            self.renderer.side_tab = action.split(":", 1)[1]
        elif action.startswith("algorithm:"):
            self.session.set_algorithm(Algorithm(action.split(":", 1)[1]))
        elif action.startswith("speed:"):
            self.session.set_speed(int(action.split(":", 1)[1]))
        elif action.startswith("heuristic:"):
            self.session.set_heuristic_mode(HeuristicMode(action.split(":", 1)[1]))
        elif action.startswith("editor_tool:") and self.editor is not None:
            self.editor.set_tool(EditorTool(action.split(":", 1)[1]))

    def _open_editor(self) -> None:
        self.session.running = False
        self.editor = MapEditor.from_maze(self.session.maze)
        self.scene = Scene.EDITOR
        self.modal = None

    def _save_editor(self) -> None:
        if self.editor is None:
            return
        try:
            path = self.editor.save(self.project_root / "maps" / "custom")
            self.session.load_custom_map(path)
        except (ValueError, OSError) as exc:
            self.editor.status = f"Save failed: {exc}"
            return
        self.scene = Scene.GAME
        self.renderer.side_tab = "play"

    def _open_replay(self) -> None:
        self.replay_index = max(0, len(self.session.replay.frames) - 1)
        self.replay_playing = False
        self.last_replay_step = monotonic()
        self.modal = "replay"

    def _export_bundle(self) -> None:
        self.export_error = ""
        try:
            self.session.export_research_bundle(self.project_root / "exports")
        except (OSError, RuntimeError) as exc:
            self.export_error = str(exc)
            self.session.status = f"Export failed: {exc}"
        self.modal = "export"

    def _update(self, now: float) -> None:
        if self.modal == "replay" and self.replay_playing:
            if now - self.last_replay_step >= 0.12:
                if self.replay_index < len(self.session.replay.frames) - 1:
                    self.replay_index += 1
                else:
                    self.replay_playing = False
                self.last_replay_step = now
            return

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
        if self.scene == Scene.EDITOR and self.editor is not None:
            self.renderer.draw_editor(self.editor, now)
            return
        self.renderer.draw_game(self.session, now, delta)
        if self.modal == "compare":
            self.renderer.draw_compare_modal(self.session, now)
        elif self.modal == "heuristics":
            self.renderer.draw_heuristic_modal(self.session)
        elif self.modal == "experiment":
            self.renderer.draw_experiment_modal(self.session)
        elif self.modal == "explain":
            self.renderer.draw_explanation_modal(self.session)
        elif self.modal == "replay":
            self.renderer.draw_replay_modal(
                self.session,
                self.replay_index,
                self.replay_playing,
            )
        elif self.modal == "export":
            self.renderer.draw_export_modal(self.session, self.export_error)
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

    def save_qa_gallery(self, output_directory: str | Path) -> list[Path]:
        """Render the major upgraded screens for automated visual review."""

        destination = Path(output_directory)
        destination.mkdir(parents=True, exist_ok=True)
        saved: list[Path] = []

        def capture(name: str) -> None:
            path = destination / name
            pygame.display.flip()
            pygame.image.save(self.screen, path)
            saved.append(path)

        now = monotonic()
        self.scene = Scene.MENU
        self.modal = None
        self._draw(now, 1.0)
        capture("01_menu.png")

        self.scene = Scene.GAME
        self.session.dynamic_ghosts = False
        target = max(
            self.session.foods | self.session.power_foods,
            key=lambda item: manhattan(self.session.player, item),
        )
        result = plan_route(
            Algorithm.A_STAR,
            self.session.maze,
            self.session.player,
            target,
            self.session.ghost_positions,
            heuristic_mode=self.session.heuristic_mode,
        )
        self.session.target = target
        self.session.last_result = result
        self.session.route = result.path[1:]
        self.renderer.explored_reveal = float(result.expanded_nodes)
        self.renderer.side_tab = "play"
        self._draw(now, 1.0)
        capture("02_gameplay.png")

        self.renderer.side_tab = "lab"
        self._draw(now, 1.0)
        capture("03_ai_lab.png")

        self.session.compare_current_problem()
        self.modal = "compare"
        self._draw(now, 1.0)
        capture("04_algorithm_comparison.png")

        self.session.compare_current_heuristics()
        self.modal = "heuristics"
        self._draw(now, 1.0)
        capture("05_heuristic_comparison.png")

        self.modal = "experiment"
        self.session.run_research_experiment()
        self._draw(now, 1.0)
        capture("06_experiment.png")

        self.modal = "explain"
        self._draw(now, 1.0)
        capture("07_explanation.png")

        self.modal = None
        self._open_editor()
        self._draw(now, 1.0)
        capture("08_map_studio.png")

        self.scene = Scene.GAME
        for step in range(8):
            self.session.step_player(now=100.0 + step * 0.1)
        self.modal = "replay"
        self.replay_index = max(0, len(self.session.replay.frames) - 1)
        self._draw(now, 1.0)
        capture("09_replay.png")

        self.session.last_export_paths = (
            Path("exports/experiment_demo.csv"),
            Path("exports/experiment_demo.pdf"),
            Path("exports/replay_demo.json"),
        )
        self.modal = "export"
        self._draw(now, 1.0)
        capture("10_export.png")
        return saved

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
