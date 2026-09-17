"""Pygame renderer for the neon pathfinding laboratory."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin
import random
from typing import Iterable

import pygame

from .editor import EditorTool, MapEditor
from .explain import explain_result
from .models import Algorithm, HeuristicMode, Position, SearchResult
from .planner import danger_penalty
from .replay import ReplayFrame
from .session import GameSession
from .settings import (
    ALGORITHM_COLORS,
    BACKGROUND_BOTTOM,
    BACKGROUND_TOP,
    BLUE,
    CYAN,
    GREEN,
    MUTED,
    ORANGE,
    PANEL,
    PANEL_LIGHT,
    PINK,
    PURPLE,
    RED,
    TEXT,
    WALL_EDGE,
    WALL_FILL,
    WINDOW_HEIGHT,
    WINDOW_WIDTH,
    YELLOW,
)


@dataclass(slots=True)
class ButtonRegion:
    rect: pygame.Rect
    action: str
    enabled: bool = True


class UIRenderer:
    """Draws menus, gameplay, modals, and interactive button regions."""

    def __init__(self, surface: pygame.Surface) -> None:
        self.surface = surface
        self.buttons: list[ButtonRegion] = []
        self.font_cache: dict[tuple[int, bool], pygame.font.Font] = {}
        self.background = self._make_gradient()
        rng = random.Random(7719)
        self.stars = [
            (rng.randrange(WINDOW_WIDTH), rng.randrange(WINDOW_HEIGHT), rng.choice((1, 1, 1, 2)))
            for _ in range(120)
        ]
        self.explored_reveal = 0.0
        self._result_identity: int | None = None
        self.side_tab = "play"
        self.maze_rect = pygame.Rect(30, 118, 868, 714)
        self.side_rect = pygame.Rect(920, 118, 490, 714)
        self.editor_grid_rect = pygame.Rect(40, 130, 1000, 700)

    def font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key not in self.font_cache:
            self.font_cache[key] = pygame.font.SysFont(
                "dejavusans,arial,sans", size, bold=bold
            )
        return self.font_cache[key]

    def _make_gradient(self) -> pygame.Surface:
        background = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        for y in range(WINDOW_HEIGHT):
            ratio = y / max(1, WINDOW_HEIGHT - 1)
            color = tuple(
                int(top + (bottom - top) * ratio)
                for top, bottom in zip(BACKGROUND_TOP, BACKGROUND_BOTTOM)
            )
            pygame.draw.line(background, color, (0, y), (WINDOW_WIDTH, y))
        return background

    def _text(
        self,
        value: str,
        position: tuple[int, int],
        size: int,
        color: tuple[int, int, int] = TEXT,
        bold: bool = False,
        anchor: str = "topleft",
    ) -> pygame.Rect:
        image = self.font(size, bold).render(value, True, color)
        rect = image.get_rect()
        setattr(rect, anchor, position)
        self.surface.blit(image, rect)
        return rect

    def _wrapped_text(
        self,
        value: str,
        rect: pygame.Rect,
        size: int,
        color: tuple[int, int, int] = MUTED,
        line_gap: int = 4,
    ) -> int:
        words = value.split()
        lines: list[str] = []
        current = ""
        font = self.font(size)
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and font.size(candidate)[0] > rect.width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current:
            lines.append(current)
        y = rect.top
        for line in lines:
            self._text(line, (rect.left, y), size, color)
            y += font.get_height() + line_gap
        return y

    def _panel(
        self,
        rect: pygame.Rect,
        border: tuple[int, int, int] = BLUE,
        alpha: int = 235,
        radius: int = 18,
    ) -> None:
        shadow = pygame.Surface((rect.width + 24, rect.height + 24), pygame.SRCALPHA)
        pygame.draw.rect(
            shadow,
            (*border, 30),
            pygame.Rect(12, 12, rect.width, rect.height),
            border_radius=radius,
        )
        self.surface.blit(shadow, (rect.x - 12, rect.y - 12))
        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*PANEL, alpha), layer.get_rect(), border_radius=radius)
        pygame.draw.rect(layer, (*border, 95), layer.get_rect(), width=1, border_radius=radius)
        self.surface.blit(layer, rect)

    def _glow_circle(
        self,
        center: tuple[int, int],
        radius: int,
        color: tuple[int, int, int],
        core: tuple[int, int, int] | None = None,
    ) -> None:
        glow_radius = max(3, radius * 3)
        glow = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        local_center = (glow_radius, glow_radius)
        for factor, alpha in ((2.6, 18), (2.0, 28), (1.5, 48)):
            pygame.draw.circle(
                glow,
                (*color, alpha),
                local_center,
                max(1, int(radius * factor)),
            )
        self.surface.blit(glow, (center[0] - glow_radius, center[1] - glow_radius))
        pygame.draw.circle(self.surface, core or color, center, radius)

    def _button(
        self,
        rect: pygame.Rect,
        label: str,
        action: str,
        accent: tuple[int, int, int] = CYAN,
        active: bool = False,
        enabled: bool = True,
        size: int = 16,
    ) -> None:
        mouse = pygame.mouse.get_pos()
        hovered = enabled and rect.collidepoint(mouse)
        fill = PANEL_LIGHT if enabled else (20, 25, 42)
        if active:
            fill = tuple(min(255, int(channel * 0.28 + 18)) for channel in accent)
        elif hovered:
            fill = (25, 40, 78)

        layer = pygame.Surface(rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*fill, 245), layer.get_rect(), border_radius=11)
        border_alpha = 230 if active or hovered else 85
        pygame.draw.rect(
            layer,
            (*accent, border_alpha),
            layer.get_rect(),
            width=2 if active else 1,
            border_radius=11,
        )
        self.surface.blit(layer, rect)
        label_color = TEXT if enabled else (88, 99, 120)
        self._text(label, rect.center, size, label_color, bold=True, anchor="center")
        self.buttons.append(ButtonRegion(rect.copy(), action, enabled))

    def action_at(self, position: tuple[int, int]) -> str | None:
        for button in reversed(self.buttons):
            if button.enabled and button.rect.collidepoint(position):
                return button.action
        return None

    def _background_details(self, now: float) -> None:
        self.surface.blit(self.background, (0, 0))
        for index, (x, y, radius) in enumerate(self.stars):
            pulse = int(35 + 35 * (0.5 + 0.5 * sin(now * 0.8 + index)))
            pygame.draw.circle(self.surface, (70, 112, 190, pulse), (x, y), radius)

        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        for offset in range(0, WINDOW_WIDTH, 180):
            y = 65 + (offset // 180 % 4) * 205
            pygame.draw.lines(
                overlay,
                (43, 92, 190, 24),
                False,
                [(offset, y), (offset + 70, y), (offset + 92, y + 22), (offset + 155, y + 22)],
                1,
            )
        self.surface.blit(overlay, (0, 0))

    def draw_menu(self, now: float) -> None:
        self.buttons.clear()
        self._background_details(now)
        self._text("CLASSICAL AI  /  INTERACTIVE PATHFINDING LAB", (72, 55), 18, CYAN, True)
        self._text("ADAPTIVE", (72, 118), 48, TEXT, True)
        self._text("PAC-MAN", (72, 170), 90, YELLOW, True)
        self._text("PATHFINDING LAB", (76, 268), 42, CYAN, True)
        self._wrapped_text(
            "Build a maze, compare five classical search algorithms, inspect every decision, and export reproducible experiment evidence.",
            pygame.Rect(78, 335, 585, 110),
            22,
            (186, 204, 232),
            8,
        )

        feature_rect = pygame.Rect(72, 472, 602, 245)
        self._panel(feature_rect, PURPLE, 210)
        features = [
            ("01", "Five algorithms", "BFS, DFS, UCS, Dijkstra, and A*"),
            ("02", "Adaptive intelligence", "Auto-selection, A* heuristics, and four ghost policies"),
            ("03", "Research workbench", "Experiments, explanations, replay, CSV, and PDF reports"),
        ]
        y = feature_rect.top + 28
        for number, title, body in features:
            self._glow_circle((feature_rect.left + 38, y + 19), 18, CYAN, PANEL_LIGHT)
            self._text(number, (feature_rect.left + 38, y + 19), 13, CYAN, True, "center")
            self._text(title, (feature_rect.left + 72, y), 20, TEXT, True)
            self._text(body, (feature_rect.left + 72, y + 29), 15, MUTED)
            y += 70

        # Hero illustration: Pac-Man, trail, and a ghost rendered from game primitives.
        hero_rect = pygame.Rect(742, 105, 620, 605)
        self._panel(hero_rect, CYAN, 175, 28)
        center = (920, 390)
        self._draw_pacman(center, 84, (1, 0), now)
        for index in range(6):
            self._glow_circle((1038 + index * 42, 390), 7, YELLOW)
        self._draw_ghost((1250, 392), 76, (255, 82, 105), False, now)
        self._text("ADAPTIVE ROUTE ENGINE", (1050, 192), 18, PINK, True, "center")
        self._text("DESIGN  /  SEARCH  /  EXPLAIN", (1050, 603), 16, MUTED, True, "center")

        start_rect = pygame.Rect(773, 744, 554, 66)
        self._button(start_rect, "START AI DEMO   [ENTER]", "start", YELLOW, size=20)
        self._text(
            "Python 3.10+  •  Pygame Community Edition  •  No internet required",
            (720, 852),
            14,
            MUTED,
            anchor="center",
        )

    def draw_game(self, session: GameSession, now: float, delta: float) -> None:
        self.buttons.clear()
        self._background_details(now)
        self._draw_header(session)
        self._panel(self.maze_rect, session.maze.config.accent, 225)
        self._panel(self.side_rect, PURPLE, 230)
        self._draw_maze(session, now, delta)
        self._draw_side_panel(session)
        self._draw_footer(session)

    def _draw_header(self, session: GameSession) -> None:
        self._text("ADAPTIVE PAC-MAN", (35, 24), 30, YELLOW, True)
        self._text("PATHFINDING LAB", (390, 29), 23, TEXT, True)
        self._text(
            f"MAP  {session.map_index + 1:02d}  /  {session.maze.config.name.upper()}",
            (37, 69),
            14,
            session.maze.config.accent,
            True,
        )

        engine = session.last_effective_algorithm.value.upper()
        if session.auto_mode:
            engine = f"AUTO→{engine}"
        items = [
            ("SCORE", f"{session.score:04d}", YELLOW),
            ("PELLETS", f"{session.collected}/{session.total_collectibles}", CYAN),
            ("LIVES", "● " * session.lives or "0", PINK),
            ("ENGINE", engine, ALGORITHM_COLORS[session.last_effective_algorithm.value]),
        ]
        x = 690
        for label, value, color in items:
            width = 145 if label != "ENGINE" else 190
            rect = pygame.Rect(x, 19, width, 70)
            layer = pygame.Surface(rect.size, pygame.SRCALPHA)
            pygame.draw.rect(layer, (*PANEL, 190), layer.get_rect(), border_radius=12)
            pygame.draw.rect(layer, (*color, 65), layer.get_rect(), width=1, border_radius=12)
            self.surface.blit(layer, rect)
            self._text(label, (rect.left + 13, rect.top + 10), 11, MUTED, True)
            self._text(value.strip(), (rect.left + 13, rect.top + 33), 19, color, True)
            x += width + 10

        help_rect = pygame.Rect(1363, 28, 42, 42)
        self._button(help_rect, "?", "help", CYAN, size=20)

    def _grid_geometry(self, session: GameSession) -> tuple[int, int, int]:
        available_height = self.maze_rect.height - 86
        cell = min(
            (self.maze_rect.width - 36) // session.maze.width,
            available_height // session.maze.height,
        )
        grid_width = cell * session.maze.width
        grid_height = cell * session.maze.height
        origin_x = self.maze_rect.centerx - grid_width // 2
        origin_y = self.maze_rect.top + 58 + (available_height - grid_height) // 2
        return origin_x, origin_y, cell

    @staticmethod
    def _cell_center(origin_x: int, origin_y: int, cell: int, position: Position) -> tuple[int, int]:
        return (
            origin_x + position[0] * cell + cell // 2,
            origin_y + position[1] * cell + cell // 2,
        )

    def _draw_maze(self, session: GameSession, now: float, delta: float) -> None:
        origin_x, origin_y, cell = self._grid_geometry(session)
        maze = session.maze
        accent = maze.config.accent

        # Base cells and weighted terrain.
        for y in range(maze.height):
            for x in range(maze.width):
                position = (x, y)
                rect = pygame.Rect(origin_x + x * cell, origin_y + y * cell, cell, cell)
                if position in maze.walls:
                    pygame.draw.rect(self.surface, WALL_FILL, rect.inflate(-2, -2), border_radius=4)
                    pygame.draw.rect(
                        self.surface,
                        WALL_EDGE,
                        rect.inflate(-3, -3),
                        width=1,
                        border_radius=4,
                    )
                    continue

                pygame.draw.rect(self.surface, (7, 13, 31), rect.inflate(-1, -1), border_radius=3)
                weight = maze.terrain_costs.get(position, 1)
                if weight > 1:
                    tint = pygame.Surface((cell - 4, cell - 4), pygame.SRCALPHA)
                    tint_color = PURPLE if weight == 2 else PINK
                    pygame.draw.rect(
                        tint,
                        (*tint_color, 44 if weight == 2 else 67),
                        tint.get_rect(),
                        border_radius=4,
                    )
                    self.surface.blit(tint, (rect.x + 2, rect.y + 2))

        result = session.last_result
        if result is not None:
            identity = id(result)
            if identity != self._result_identity:
                self._result_identity = identity
                self.explored_reveal = 0.0
            self.explored_reveal = min(
                float(result.expanded_nodes), self.explored_reveal + max(1.0, delta * 230)
            )
            reveal_count = int(self.explored_reveal)
            explored_layer = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
            for index, position in enumerate(result.explored_order[:reveal_count]):
                if position in {session.player, session.target}:
                    continue
                rect = pygame.Rect(
                    origin_x + position[0] * cell + 5,
                    origin_y + position[1] * cell + 5,
                    max(3, cell - 10),
                    max(3, cell - 10),
                )
                alpha = 32 + int(28 * index / max(1, reveal_count))
                pygame.draw.rect(explored_layer, (*accent, alpha), rect, border_radius=3)
            self.surface.blit(explored_layer, (0, 0))

            visible_path = [position for position in result.path if position == session.player or position in session.route]
            if len(visible_path) >= 2:
                points = [self._cell_center(origin_x, origin_y, cell, position) for position in visible_path]
                glow = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
                pygame.draw.lines(glow, (*accent, 60), False, points, max(4, cell // 3))
                self.surface.blit(glow, (0, 0))
                pygame.draw.lines(self.surface, accent, False, points, max(2, cell // 9))
                for point in points[:: max(1, len(points) // 10)]:
                    pygame.draw.circle(self.surface, TEXT, point, max(1, cell // 12))

        # Cell-level risk heatmap plus soft rings make weighted search visible.
        danger_layer = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
        if not session.is_frightened(now):
            if session.show_heatmap:
                for y in range(maze.height):
                    for x in range(maze.width):
                        position = (x, y)
                        if not maze.is_walkable(position):
                            continue
                        penalty = danger_penalty(position, session.ghost_positions)
                        if penalty <= 0:
                            continue
                        alpha = min(115, 14 + int(penalty * 2.3))
                        color = RED if penalty >= 12 else ORANGE
                        rect = pygame.Rect(
                            origin_x + x * cell + 2,
                            origin_y + y * cell + 2,
                            max(2, cell - 4),
                            max(2, cell - 4),
                        )
                        pygame.draw.rect(
                            danger_layer,
                            (*color, alpha),
                            rect,
                            border_radius=max(1, cell // 7),
                        )
            for ghost in session.ghosts:
                gx, gy = self._cell_center(origin_x, origin_y, cell, ghost.position)
                pygame.draw.circle(danger_layer, (*RED, 18), (gx, gy), cell * 3)
                pygame.draw.circle(danger_layer, (*ORANGE, 24), (gx, gy), cell * 2)
        self.surface.blit(danger_layer, (0, 0))

        # Collectibles.
        pulse = 0.5 + 0.5 * sin(now * 5)
        for position in session.foods:
            center = self._cell_center(origin_x, origin_y, cell, position)
            self._glow_circle(center, max(2, cell // 9), YELLOW)
        for position in session.power_foods:
            center = self._cell_center(origin_x, origin_y, cell, position)
            self._glow_circle(center, max(5, cell // 5 + int(pulse * 2)), PINK, TEXT)

        self._draw_exit(
            self._cell_center(origin_x, origin_y, cell, maze.exit),
            cell,
            unlocked=not session.foods and not session.power_foods,
            now=now,
        )

        if session.target is not None:
            center = self._cell_center(origin_x, origin_y, cell, session.target)
            radius = int(cell * (0.35 + 0.08 * pulse))
            pygame.draw.circle(self.surface, accent, center, radius, width=2)

        frightened = session.is_frightened(now)
        for ghost in session.ghosts:
            center = self._cell_center(origin_x, origin_y, cell, ghost.position)
            self._draw_ghost(center, int(cell * 0.78), ghost.color, frightened, now)

        self._draw_pacman(
            self._cell_center(origin_x, origin_y, cell, session.player),
            int(cell * 0.77),
            session.player_direction,
            now,
        )

        label_rect = pygame.Rect(self.maze_rect.left + 18, self.maze_rect.top + 14, 280, 30)
        layer = pygame.Surface(label_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(layer, (*PANEL, 225), layer.get_rect(), border_radius=8)
        self.surface.blit(layer, label_rect)
        self._text("LIVE GRID  /  SEARCH VISUALIZATION", label_rect.center, 12, accent, True, "center")

    def _draw_pacman(
        self,
        center: tuple[int, int],
        diameter: int,
        direction: Position,
        now: float,
    ) -> None:
        radius = max(6, diameter // 2)
        self._glow_circle(center, radius, YELLOW)
        angle = {"1,0": 0.0, "-1,0": pi, "0,-1": -pi / 2, "0,1": pi / 2}.get(
            f"{direction[0]},{direction[1]}", 0.0
        )
        mouth = 0.25 + 0.18 * (0.5 + 0.5 * sin(now * 11))
        points = [
            center,
            (
                int(center[0] + radius * 1.15 * cos(angle - mouth)),
                int(center[1] + radius * 1.15 * sin(angle - mouth)),
            ),
            (
                int(center[0] + radius * 1.15 * cos(angle + mouth)),
                int(center[1] + radius * 1.15 * sin(angle + mouth)),
            ),
        ]
        pygame.draw.polygon(self.surface, (7, 13, 31), points)

    def _draw_ghost(
        self,
        center: tuple[int, int],
        diameter: int,
        color: tuple[int, int, int],
        frightened: bool,
        now: float,
    ) -> None:
        width = max(12, diameter)
        height = max(14, int(diameter * 1.04))
        ghost_color = (79, 107, 255) if frightened else color
        x = center[0] - width // 2
        y = center[1] - height // 2
        glow = pygame.Surface((width * 3, height * 3), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*ghost_color, 42), (width * 3 // 2, height * 3 // 2), width)
        self.surface.blit(glow, (center[0] - width * 3 // 2, center[1] - height * 3 // 2))
        pygame.draw.circle(self.surface, ghost_color, (center[0], y + width // 2), width // 2)
        pygame.draw.rect(
            self.surface,
            ghost_color,
            pygame.Rect(x, y + width // 2, width, height - width // 2 - 3),
        )
        foot_y = y + height - 3
        foot_radius = max(2, width // 7)
        for index in range(4):
            pygame.draw.circle(
                self.surface,
                ghost_color,
                (x + foot_radius + index * max(1, (width - 2 * foot_radius) // 3), foot_y),
                foot_radius,
            )

        eye_y = y + height // 3
        eye_dx = width // 5
        for eye_x in (center[0] - eye_dx, center[0] + eye_dx):
            pygame.draw.circle(self.surface, TEXT, (eye_x, eye_y), max(2, width // 8))
            pupil_x = eye_x + int(2 * sin(now * 2))
            pygame.draw.circle(self.surface, (20, 33, 74), (pupil_x, eye_y), max(1, width // 15))

    def _draw_exit(
        self,
        center: tuple[int, int],
        cell: int,
        unlocked: bool,
        now: float,
    ) -> None:
        color = GREEN if unlocked else RED
        width = max(12, int(cell * 0.65))
        rect = pygame.Rect(center[0] - width // 2, center[1] - width // 2, width, width)
        pygame.draw.rect(self.surface, (10, 25, 35), rect, border_radius=4)
        pygame.draw.rect(self.surface, color, rect, width=2, border_radius=4)
        bar_x = center[0] + int(sin(now * 3) * 2)
        pygame.draw.line(
            self.surface,
            color,
            (bar_x, rect.top + 4),
            (bar_x, rect.bottom - 4),
            width=2,
        )

    def _draw_side_panel(self, session: GameSession) -> None:
        x = self.side_rect.left + 20
        width = self.side_rect.width - 40
        tab_width = (width - 8) // 2
        self._button(
            pygame.Rect(x, 136, tab_width, 38),
            "PLAY CONTROL",
            "tab:play",
            CYAN,
            active=self.side_tab == "play",
            size=13,
        )
        self._button(
            pygame.Rect(x + tab_width + 8, 136, tab_width, 38),
            "AI WORKBENCH",
            "tab:lab",
            PURPLE,
            active=self.side_tab == "lab",
            size=13,
        )

        if self.side_tab == "lab":
            self._draw_lab_tab(session, x, width)
        else:
            self._draw_play_tab(session, x, width)

    def _draw_play_tab(self, session: GameSession, x: int, width: int) -> None:
        accent = ALGORITHM_COLORS[session.last_effective_algorithm.value]
        self._text("SELECT SEARCH ENGINE", (x, 190), 15, TEXT, True)
        description = (
            f"AUTO: {session.auto_reason}"
            if session.auto_mode
            else session.algorithm.short_description
        )
        self._wrapped_text(description, pygame.Rect(x, 214, width, 38), 12, MUTED, 2)

        algorithms = list(Algorithm)
        button_width = (width - 10) // 2
        for index, algorithm in enumerate(algorithms):
            row = index // 2
            column = index % 2
            rect = (
                pygame.Rect(x, 352, width, 40)
                if index == 4
                else pygame.Rect(
                    x + column * (button_width + 10),
                    258 + row * 47,
                    button_width,
                    40,
                )
            )
            self._button(
                rect,
                f"{index + 1}  {algorithm.value.upper()}",
                f"algorithm:{algorithm.value}",
                ALGORITHM_COLORS[algorithm.value],
                active=not session.auto_mode and session.algorithm == algorithm,
                size=14,
            )

        pygame.draw.line(self.surface, (55, 70, 110), (x, 405), (x + width, 405), 1)
        half = (width - 10) // 2
        run_label = "STOP AI" if session.running else "RUN AI"
        self._button(
            pygame.Rect(x, 419, half, 40),
            run_label,
            "toggle_run",
            GREEN if not session.running else RED,
            active=session.running,
        )
        self._button(pygame.Rect(x + half + 10, 419, half, 40), "STEP ONCE", "step", CYAN)
        self._button(pygame.Rect(x, 467, half, 40), "COMPARE", "compare", PURPLE)
        self._button(pygame.Rect(x + half + 10, 467, half, 40), "RESET", "reset", ORANGE)
        self._button(pygame.Rect(x, 515, half, 40), "NEXT MAP", "next_map", PINK)
        ghost_label = "GHOSTS: LIVE" if session.dynamic_ghosts else "GHOSTS: FROZEN"
        self._button(
            pygame.Rect(x + half + 10, 515, half, 40),
            ghost_label,
            "toggle_ghosts",
            RED if session.dynamic_ghosts else MUTED,
            active=session.dynamic_ghosts,
            size=12,
        )

        mission_rect = pygame.Rect(x, 570, width, 82)
        pygame.draw.rect(self.surface, (15, 26, 58), mission_rect, border_radius=12)
        pygame.draw.rect(self.surface, accent, mission_rect, width=1, border_radius=12)
        self._text("MISSION PROGRESS", (mission_rect.left + 14, mission_rect.top + 10), 11, MUTED, True)
        self._text(
            f"{session.collected} of {session.total_collectibles} pellets secured",
            (mission_rect.left + 14, mission_rect.top + 30),
            14,
            TEXT,
            True,
        )
        track = pygame.Rect(mission_rect.left + 14, mission_rect.top + 57, mission_rect.width - 28, 10)
        pygame.draw.rect(self.surface, (30, 40, 72), track, border_radius=5)
        fill = track.copy()
        fill.width = max(0, int(track.width * session.progress))
        if fill.width:
            pygame.draw.rect(self.surface, accent, fill, border_radius=5)

        result = session.last_result
        metrics_rect = pygame.Rect(x, 662, width, 98)
        pygame.draw.rect(self.surface, (15, 26, 58), metrics_rect, border_radius=12)
        labels = (
            ("STEPS", str(result.steps) if result else "–"),
            ("COST", f"{result.path_cost:.0f}" if result else "–"),
            ("EXPANDED", str(result.expanded_nodes) if result else "–"),
            ("TIME", f"{result.elapsed_ms:.3f} ms" if result else "–"),
        )
        item_width = metrics_rect.width // 2
        for index, (label, value) in enumerate(labels):
            left = metrics_rect.left + (index % 2) * item_width + 14
            top = metrics_rect.top + (index // 2) * 43 + 8
            self._text(label, (left, top), 9, MUTED, True)
            self._text(value, (left, top + 16), 15, accent, True)

        self._text("SPEED", (x, 785), 10, MUTED, True)
        speed_x = x + 70
        for speed in (1, 2, 4):
            self._button(
                pygame.Rect(speed_x, 774, 58, 30),
                f"{speed}×",
                f"speed:{speed}",
                accent,
                active=session.speed == speed,
                size=12,
            )
            speed_x += 66
        mode = "POWER MODE" if session.is_frightened() else session.status.upper()
        self._text(mode[:47], (self.side_rect.right - 20, 817), 9, MUTED, True, "bottomright")

    def _draw_lab_tab(self, session: GameSession, x: int, width: int) -> None:
        self._text("ADAPTIVE SEARCH CONTROLS", (x, 190), 15, TEXT, True)
        auto_label = (
            f"AUTO SELECTOR: ON  →  {session.last_effective_algorithm.value.upper()}"
            if session.auto_mode
            else "AUTO SELECTOR: OFF"
        )
        self._button(
            pygame.Rect(x, 216, width, 42),
            auto_label,
            "toggle_auto",
            GREEN,
            active=session.auto_mode,
            size=13,
        )

        self._text("A* HEURISTIC", (x, 276), 11, MUTED, True)
        gap = 7
        heuristic_width = (width - gap * 2) // 3
        for index, mode in enumerate(HeuristicMode):
            self._button(
                pygame.Rect(x + index * (heuristic_width + gap), 298, heuristic_width, 38),
                mode.value.upper(),
                f"heuristic:{mode.value}",
                PINK,
                active=session.heuristic_mode is mode,
                size=11,
            )

        half = (width - 10) // 2
        ghost_mode = "GHOST AI: ADVANCED" if session.advanced_ghost_ai else "GHOST AI: CLASSIC"
        self._button(
            pygame.Rect(x, 352, half, 40),
            ghost_mode,
            "toggle_ghost_ai",
            RED,
            active=session.advanced_ghost_ai,
            size=11,
        )
        self._button(
            pygame.Rect(x + half + 10, 352, half, 40),
            "RISK HEATMAP",
            "toggle_heatmap",
            ORANGE,
            active=session.show_heatmap,
            size=11,
        )

        self._text("RESEARCH TOOLS", (x, 414), 11, MUTED, True)
        tools = [
            ("HEURISTICS", "heuristic_compare", PINK),
            ("EXPERIMENT", "experiment", PURPLE),
            ("EXPLAIN ROUTE", "explain", CYAN),
            ("REPLAY", "replay", BLUE),
            ("EXPORT CSV/PDF", "export_bundle", GREEN),
            ("MAP STUDIO", "editor", YELLOW),
        ]
        for index, (label, action, color) in enumerate(tools):
            column = index % 2
            row = index // 2
            self._button(
                pygame.Rect(x + column * (half + 10), 436 + row * 48, half, 40),
                label,
                action,
                color,
                size=12,
            )

        insight = pygame.Rect(x, 592, width, 164)
        pygame.draw.rect(self.surface, (15, 26, 58), insight, border_radius=12)
        pygame.draw.rect(self.surface, (*PURPLE,), insight, width=1, border_radius=12)
        self._text("LIVE INTELLIGENCE", (insight.left + 14, insight.top + 11), 11, PURPLE, True)
        if session.auto_mode:
            y = self._wrapped_text(
                session.auto_reason.capitalize() + ".",
                pygame.Rect(insight.left + 14, insight.top + 34, insight.width - 28, 42),
                12,
                TEXT,
                2,
            )
        else:
            y = self._wrapped_text(
                f"Manual {session.algorithm.value}: {session.algorithm.short_description}.",
                pygame.Rect(insight.left + 14, insight.top + 34, insight.width - 28, 42),
                12,
                TEXT,
                2,
            )
        self._text("GHOST TEAM", (insight.left + 14, y + 8), 10, MUTED, True)
        roster = "  •  ".join(
            f"{ghost.name}: {ghost.behavior.value}" for ghost in session.ghosts
        )
        self._wrapped_text(
            roster or "No ghosts on this map",
            pygame.Rect(insight.left + 14, y + 27, insight.width - 28, 50),
            11,
            MUTED,
            2,
        )
        self._text(session.status.upper()[:48], (self.side_rect.right - 20, 817), 9, MUTED, True, "bottomright")

    def _draw_footer(self, session: GameSession) -> None:
        self._text(
            "ENTER run   SPACE pause   S step   C compare   L workbench   E explain   X experiment   F studio   H help",
            (35, 867),
            12,
            MUTED,
        )
        target = session.target
        target_text = f"TARGET {target[0]},{target[1]}" if target else "TARGET AUTO"
        self._text(target_text, (1405, 867), 13, session.maze.config.accent, True, "topright")

    def draw_compare_modal(self, session: GameSession, now: float) -> None:
        self.buttons.clear()
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((1, 3, 12, 210))
        self.surface.blit(overlay, (0, 0))
        rect = pygame.Rect(170, 135, 1100, 620)
        self._panel(rect, PURPLE, 250, 24)
        self._text("ALGORITHM COMPARISON", (rect.left + 38, rect.top + 30), 29, TEXT, True)
        target = session.comparison_target()
        self._text(
            f"Same snapshot: start {session.player}  /  target {target}  /  A*: {session.heuristic_mode.value}",
            (rect.left + 38, rect.top + 71),
            15,
            MUTED,
        )

        headers = ("ALGORITHM", "FOUND", "STEPS", "COST", "EXPANDED", "FRONTIER", "TIME")
        starts = (210, 450, 565, 665, 770, 920, 1055)
        y = rect.top + 128
        for header, x in zip(headers, starts):
            self._text(header, (x, y), 12, MUTED, True)
        pygame.draw.line(self.surface, (68, 82, 129), (205, y + 27), (1230, y + 27), 1)

        max_expanded = max(
            (result.expanded_nodes for result in session.comparison_results), default=1
        )
        y += 48
        for result in session.comparison_results:
            active = result.algorithm == session.algorithm
            row = pygame.Rect(198, y - 10, 1037, 62)
            if active:
                layer = pygame.Surface(row.size, pygame.SRCALPHA)
                pygame.draw.rect(
                    layer,
                    (*ALGORITHM_COLORS[result.algorithm.value], 30),
                    layer.get_rect(),
                    border_radius=10,
                )
                self.surface.blit(layer, row)
            values = (
                result.algorithm.value,
                "YES" if result.found else "NO",
                str(result.steps),
                f"{result.path_cost:.0f}",
                str(result.expanded_nodes),
                str(result.frontier_peak),
                f"{result.elapsed_ms:.3f} ms",
            )
            color = ALGORITHM_COLORS[result.algorithm.value]
            for index, (value, x) in enumerate(zip(values, starts)):
                self._text(value, (x, y), 17 if index == 0 else 15, color if index == 0 else TEXT, index == 0)
            bar_width = int(300 * result.expanded_nodes / max(1, max_expanded))
            pygame.draw.rect(
                self.surface,
                (33, 43, 78),
                pygame.Rect(210, y + 29, 300, 5),
                border_radius=3,
            )
            pygame.draw.rect(
                self.surface,
                color,
                pygame.Rect(210, y + 29, max(3, bar_width), 5),
                border_radius=3,
            )
            y += 72

        note_rect = pygame.Rect(rect.left + 38, rect.bottom - 91, 810, 54)
        self._wrapped_text(
            "Interpretation: fewer expanded nodes means less search work. UCS and Dijkstra normally match because costs are non-negative. A* uses the selected heuristic while every algorithm receives the same snapshot.",
            note_rect,
            14,
            MUTED,
            3,
        )
        self._button(
            pygame.Rect(rect.right - 200, rect.bottom - 83, 160, 45),
            "CLOSE  [ESC]",
            "close_modal",
            CYAN,
        )

    def draw_heuristic_modal(self, session: GameSession) -> None:
        self.buttons.clear()
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((1, 3, 12, 214))
        self.surface.blit(overlay, (0, 0))
        rect = pygame.Rect(235, 165, 970, 570)
        self._panel(rect, PINK, 252, 24)
        self._text("A* HEURISTIC LAB", (rect.left + 38, rect.top + 30), 30, TEXT, True)
        self._text(
            "Three A* variants, one unchanged maze snapshot",
            (rect.left + 38, rect.top + 71),
            15,
            MUTED,
        )
        headers = ("MODE", "STEPS", "COST", "EXPANDED", "FRONTIER", "TIME", "OPTIMAL?")
        starts = (285, 520, 610, 700, 835, 945, 1080)
        y = rect.top + 125
        for label, x in zip(headers, starts):
            self._text(label, (x, y), 11, MUTED, True)
        pygame.draw.line(self.surface, (68, 82, 129), (275, y + 25), (1160, y + 25), 1)
        y += 55
        max_expanded = max((item.expanded_nodes for item in session.heuristic_results), default=1)
        for result in session.heuristic_results:
            mode = result.heuristic_mode or HeuristicMode.MANHATTAN
            active = mode is session.heuristic_mode
            row = pygame.Rect(270, y - 12, 895, 78)
            layer = pygame.Surface(row.size, pygame.SRCALPHA)
            pygame.draw.rect(
                layer,
                (*PINK, 34 if active else 12),
                layer.get_rect(),
                border_radius=11,
            )
            self.surface.blit(layer, row)
            values = (
                mode.value,
                str(result.steps),
                f"{result.path_cost:.0f}",
                str(result.expanded_nodes),
                str(result.frontier_peak),
                f"{result.elapsed_ms:.3f}",
                "YES" if mode.guarantees_optimality else "NO",
            )
            for index, (value, x) in enumerate(zip(values, starts)):
                self._text(value, (x, y), 16 if index == 0 else 14, PINK if index == 0 else TEXT, index == 0)
            bar = pygame.Rect(285, y + 31, 310, 6)
            pygame.draw.rect(self.surface, (32, 44, 80), bar, border_radius=3)
            fill = bar.copy()
            fill.width = max(3, int(bar.width * result.expanded_nodes / max_expanded))
            pygame.draw.rect(self.surface, PINK, fill, border_radius=3)
            self._text(mode.description, (620, y + 27), 11, MUTED)
            y += 92
        self._wrapped_text(
            "Manhattan is usually strongest for four-direction grids. Euclidean remains admissible but gives a weaker estimate. Weighted A* may expand fewer cells by trading away the optimality guarantee.",
            pygame.Rect(rect.left + 40, rect.bottom - 95, 700, 58),
            13,
            MUTED,
            3,
        )
        self._button(
            pygame.Rect(rect.right - 200, rect.bottom - 76, 160, 43),
            "CLOSE  [ESC]",
            "close_modal",
            CYAN,
        )

    def draw_experiment_modal(self, session: GameSession) -> None:
        self.buttons.clear()
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((1, 3, 12, 218))
        self.surface.blit(overlay, (0, 0))
        rect = pygame.Rect(115, 92, 1210, 716)
        self._panel(rect, PURPLE, 252, 24)
        report = session.experiment_report
        self._text("REPRODUCIBLE EXPERIMENT", (rect.left + 38, rect.top + 28), 29, TEXT, True)
        if report is None:
            self._text("Run the experiment to generate results.", rect.center, 18, MUTED, anchor="center")
            return
        self._text(
            f"{report.map_name}  •  {len(report.scenarios)} fixed targets  •  three timing samples per algorithm",
            (rect.left + 38, rect.top + 68),
            14,
            MUTED,
        )

        headers = ("ALGORITHM", "SUCCESS", "AVG STEPS", "AVG COST", "AVG EXPANDED", "AVG MS")
        starts = (160, 365, 470, 595, 710, 865)
        y = rect.top + 118
        for label, x in zip(headers, starts):
            self._text(label, (x, y), 10, MUTED, True)
        y += 38
        summaries = report.algorithm_summaries
        max_expanded = max((item.average_expanded for item in summaries), default=1.0)
        for summary in summaries:
            color = ALGORITHM_COLORS[summary.label]
            values = (
                summary.label,
                f"{summary.successful}/{summary.scenarios}",
                f"{summary.average_steps:.1f}",
                f"{summary.average_cost:.1f}",
                f"{summary.average_expanded:.1f}",
                f"{summary.average_ms:.4f}",
            )
            for index, (value, x) in enumerate(zip(values, starts)):
                self._text(value, (x, y), 15, color if index == 0 else TEXT, index == 0)
            chart = pygame.Rect(980, y + 2, 275, 12)
            pygame.draw.rect(self.surface, (31, 42, 76), chart, border_radius=6)
            fill = chart.copy()
            fill.width = max(4, int(chart.width * summary.average_expanded / max_expanded))
            pygame.draw.rect(self.surface, color, fill, border_radius=6)
            y += 55

        heuristic_rect = pygame.Rect(rect.left + 38, rect.top + 455, 720, 188)
        pygame.draw.rect(self.surface, (14, 24, 55), heuristic_rect, border_radius=14)
        pygame.draw.rect(self.surface, (*PINK,), heuristic_rect, width=1, border_radius=14)
        self._text("A* HEURISTIC SUMMARY", (heuristic_rect.left + 18, heuristic_rect.top + 14), 13, PINK, True)
        hx = (heuristic_rect.left + 18, heuristic_rect.left + 240, heuristic_rect.left + 355, heuristic_rect.left + 500, heuristic_rect.left + 620)
        for label, x in zip(("MODE", "STEPS", "COST", "EXPANDED", "MS"), hx):
            self._text(label, (x, heuristic_rect.top + 43), 9, MUTED, True)
        hy = heuristic_rect.top + 68
        for item in report.heuristic_summaries:
            for value, x in zip(
                (
                    item.label,
                    f"{item.average_steps:.1f}",
                    f"{item.average_cost:.1f}",
                    f"{item.average_expanded:.1f}",
                    f"{item.average_ms:.4f}",
                ),
                hx,
            ):
                self._text(value, (x, hy), 12, TEXT)
            hy += 34

        note = pygame.Rect(rect.left + 785, rect.top + 455, 385, 188)
        pygame.draw.rect(self.surface, (14, 24, 55), note, border_radius=14)
        pygame.draw.rect(self.surface, (*GREEN,), note, width=1, border_radius=14)
        self._text("EVIDENCE OUTPUT", (note.left + 18, note.top + 14), 13, GREEN, True)
        self._wrapped_text(
            "Export creates a detailed CSV, a presentation-ready PDF summary, and a JSON replay. Timing varies by computer; route cost, steps, and expansion counts are deterministic for the same snapshot.",
            pygame.Rect(note.left + 18, note.top + 43, note.width - 36, 105),
            12,
            MUTED,
            4,
        )
        self._button(
            pygame.Rect(note.left + 18, note.bottom - 50, 170, 35),
            "EXPORT BUNDLE",
            "export_bundle",
            GREEN,
            size=11,
        )
        self._button(
            pygame.Rect(rect.right - 195, rect.bottom - 53, 155, 36),
            "CLOSE  [ESC]",
            "close_modal",
            CYAN,
            size=12,
        )

    def draw_explanation_modal(self, session: GameSession) -> None:
        self.buttons.clear()
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((1, 3, 12, 216))
        self.surface.blit(overlay, (0, 0))
        rect = pygame.Rect(215, 115, 1010, 670)
        accent = ALGORITHM_COLORS[session.last_effective_algorithm.value]
        self._panel(rect, accent, 252, 24)
        explanation = explain_result(
            session.last_effective_algorithm,
            session.last_result,
            session.heuristic_mode,
            auto_reason=session.auto_reason if session.auto_mode else "",
        )
        self._text("EXPLAINABLE AI", (rect.left + 40, rect.top + 31), 14, accent, True)
        self._text(explanation.title.upper(), (rect.left + 40, rect.top + 58), 29, TEXT, True)
        cards = [
            ("DATA STRUCTURE", explanation.data_structure),
            ("EXPANSION RULE", explanation.priority_rule),
            ("CORRECTNESS", explanation.guarantee),
            ("ROUTE REASON", explanation.route_reason),
            ("CURRENT EVIDENCE", explanation.observation),
        ]
        y = rect.top + 118
        for index, (label, body) in enumerate(cards):
            height = 86 if index < 4 else 112
            card = pygame.Rect(rect.left + 40, y, rect.width - 80, height)
            pygame.draw.rect(self.surface, (14, 24, 55), card, border_radius=12)
            pygame.draw.rect(self.surface, (*accent,), card, width=1, border_radius=12)
            self._text(f"{index + 1:02d}  {label}", (card.left + 16, card.top + 13), 11, accent, True)
            self._wrapped_text(
                body,
                pygame.Rect(card.left + 16, card.top + 37, card.width - 32, card.height - 44),
                14,
                TEXT,
                3,
            )
            y += height + 10
        self._button(
            pygame.Rect(rect.right - 200, rect.bottom - 58, 160, 40),
            "CLOSE  [ESC]",
            "close_modal",
            CYAN,
            size=12,
        )

    def _draw_replay_grid(
        self,
        session: GameSession,
        frame: ReplayFrame,
        rect: pygame.Rect,
    ) -> None:
        maze = session.maze
        cell = min(rect.width // maze.width, rect.height // maze.height)
        width = cell * maze.width
        height = cell * maze.height
        ox = rect.centerx - width // 2
        oy = rect.centery - height // 2
        for y in range(maze.height):
            for x in range(maze.width):
                position = (x, y)
                cell_rect = pygame.Rect(ox + x * cell, oy + y * cell, cell, cell)
                if position in maze.walls:
                    pygame.draw.rect(self.surface, WALL_FILL, cell_rect.inflate(-1, -1), border_radius=2)
                    pygame.draw.rect(self.surface, WALL_EDGE, cell_rect.inflate(-2, -2), width=1, border_radius=2)
                else:
                    pygame.draw.rect(self.surface, (7, 13, 31), cell_rect.inflate(-1, -1), border_radius=2)
        if len(frame.route) > 1:
            points = [self._cell_center(ox, oy, cell, position) for position in frame.route]
            pygame.draw.lines(self.surface, PINK, False, points, max(2, cell // 7))
        for position in frame.ghosts:
            self._draw_ghost(self._cell_center(ox, oy, cell, position), int(cell * 0.72), RED, False, 0.0)
        self._draw_pacman(
            self._cell_center(ox, oy, cell, frame.player),
            int(cell * 0.74),
            (1, 0),
            0.0,
        )

    def draw_replay_modal(
        self,
        session: GameSession,
        index: int,
        playing: bool,
    ) -> None:
        self.buttons.clear()
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((1, 3, 12, 220))
        self.surface.blit(overlay, (0, 0))
        rect = pygame.Rect(105, 82, 1230, 735)
        self._panel(rect, BLUE, 252, 24)
        frames = session.replay.frames
        if not frames:
            self._text("No replay frames are available.", rect.center, 18, MUTED, anchor="center")
            return
        safe_index = max(0, min(index, len(frames) - 1))
        frame = frames[safe_index]
        self._text("MISSION REPLAY", (rect.left + 36, rect.top + 26), 29, TEXT, True)
        self._text(
            f"Frame {safe_index + 1} / {len(frames)}  •  Tick {frame.tick}  •  Event: {frame.event}",
            (rect.left + 36, rect.top + 65),
            14,
            MUTED,
        )
        grid_rect = pygame.Rect(rect.left + 30, rect.top + 105, 790, 540)
        pygame.draw.rect(self.surface, (6, 11, 28), grid_rect, border_radius=15)
        pygame.draw.rect(self.surface, (*BLUE,), grid_rect, width=1, border_radius=15)
        self._draw_replay_grid(session, frame, grid_rect.inflate(-18, -18))

        info = pygame.Rect(rect.left + 846, rect.top + 105, 350, 540)
        pygame.draw.rect(self.surface, (14, 24, 55), info, border_radius=15)
        self._text("FRAME TELEMETRY", (info.left + 20, info.top + 20), 13, BLUE, True)
        values = [
            ("Score", str(frame.score)),
            ("Lives", str(frame.lives)),
            ("Pellets", str(frame.collected)),
            ("Player", str(frame.player)),
            ("Target", str(frame.target or "Auto")),
            ("Route cells", str(len(frame.route))),
        ]
        y = info.top + 60
        for label, value in values:
            self._text(label, (info.left + 20, y), 12, MUTED)
            self._text(value, (info.right - 20, y), 14, TEXT, True, "topright")
            y += 38
        self._text("STATUS", (info.left + 20, y + 8), 10, MUTED, True)
        self._wrapped_text(
            frame.status,
            pygame.Rect(info.left + 20, y + 28, info.width - 40, 90),
            13,
            TEXT,
            3,
        )
        timeline = pygame.Rect(info.left + 20, info.bottom - 104, info.width - 40, 9)
        pygame.draw.rect(self.surface, (34, 46, 82), timeline, border_radius=5)
        progress = timeline.copy()
        progress.width = max(4, int(timeline.width * safe_index / max(1, len(frames) - 1)))
        pygame.draw.rect(self.surface, BLUE, progress, border_radius=5)
        half = (info.width - 50) // 3
        self._button(pygame.Rect(info.left + 20, info.bottom - 75, half, 38), "◀", "replay_prev", BLUE)
        self._button(
            pygame.Rect(info.left + 25 + half, info.bottom - 75, half, 38),
            "PAUSE" if playing else "PLAY",
            "replay_toggle",
            GREEN,
            active=playing,
            size=11,
        )
        self._button(pygame.Rect(info.left + 30 + half * 2, info.bottom - 75, half, 38), "▶", "replay_next", BLUE)
        self._button(
            pygame.Rect(rect.left + 35, rect.bottom - 64, 180, 38),
            "SAVE REPLAY",
            "save_replay",
            GREEN,
            size=12,
        )
        self._button(
            pygame.Rect(rect.right - 195, rect.bottom - 64, 160, 38),
            "CLOSE  [ESC]",
            "close_modal",
            CYAN,
            size=12,
        )

    def draw_export_modal(self, session: GameSession, error: str = "") -> None:
        self.buttons.clear()
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((1, 3, 12, 218))
        self.surface.blit(overlay, (0, 0))
        rect = pygame.Rect(365, 245, 710, 410)
        color = RED if error else GREEN
        self._panel(rect, color, 252, 24)
        title = "EXPORT FAILED" if error else "RESEARCH BUNDLE READY"
        self._text(title, (rect.centerx, rect.top + 52), 30, color, True, "center")
        if error:
            self._wrapped_text(error, pygame.Rect(rect.left + 55, rect.top + 115, rect.width - 110, 120), 15, TEXT, 5)
        else:
            self._text("Saved inside the project exports folder:", (rect.left + 55, rect.top + 115), 15, MUTED)
            y = rect.top + 155
            for path in session.last_export_paths:
                self._text("●", (rect.left + 58, y + 1), 13, color, True)
                self._text(path.name, (rect.left + 82, y), 15, TEXT, True)
                y += 38
            self._wrapped_text(
                "The CSV contains raw scenario data, the PDF contains summary tables, and the JSON file stores the replay timeline.",
                pygame.Rect(rect.left + 55, y + 12, rect.width - 110, 70),
                13,
                MUTED,
                3,
            )
        self._button(
            pygame.Rect(rect.centerx - 90, rect.bottom - 68, 180, 42),
            "CLOSE",
            "close_modal",
            CYAN,
        )

    def draw_editor(self, editor: MapEditor, now: float) -> None:
        self.buttons.clear()
        self._background_details(now)
        self._text("MAP STUDIO", (38, 25), 33, YELLOW, True)
        self._text("SAFE CUSTOM MAZE EDITOR", (285, 33), 20, TEXT, True)
        self._text(
            "Edits use a copy. Packaged maps remain unchanged until a new validated JSON map is saved.",
            (40, 76),
            13,
            MUTED,
        )
        grid_panel = pygame.Rect(30, 112, 1015, 735)
        tools_panel = pygame.Rect(1065, 112, 345, 735)
        self._panel(grid_panel, editor.maze.config.accent, 235)
        self._panel(tools_panel, PURPLE, 240)

        available = grid_panel.inflate(-34, -34)
        cell = min(available.width // editor.maze.width, available.height // editor.maze.height)
        grid_width = cell * editor.maze.width
        grid_height = cell * editor.maze.height
        ox = available.centerx - grid_width // 2
        oy = available.centery - grid_height // 2
        self.editor_grid_rect = pygame.Rect(ox, oy, grid_width, grid_height)

        maze = editor.maze
        for y in range(maze.height):
            for x in range(maze.width):
                position = (x, y)
                rect = pygame.Rect(ox + x * cell, oy + y * cell, cell, cell)
                if position in maze.walls:
                    pygame.draw.rect(self.surface, WALL_FILL, rect.inflate(-2, -2), border_radius=3)
                    pygame.draw.rect(self.surface, WALL_EDGE, rect.inflate(-3, -3), width=1, border_radius=3)
                    continue
                pygame.draw.rect(self.surface, (7, 13, 31), rect.inflate(-1, -1), border_radius=2)
                cost = maze.terrain_costs.get(position, 1)
                if cost > 1:
                    color = PURPLE if cost == 2 else PINK
                    layer = pygame.Surface((max(2, cell - 4), max(2, cell - 4)), pygame.SRCALPHA)
                    layer.fill((*color, 70))
                    self.surface.blit(layer, (rect.x + 2, rect.y + 2))
        for position in maze.foods:
            self._glow_circle(self._cell_center(ox, oy, cell, position), max(2, cell // 9), YELLOW)
        for position in maze.power_foods:
            self._glow_circle(self._cell_center(ox, oy, cell, position), max(4, cell // 5), PINK, TEXT)
        for position in maze.ghost_starts:
            self._draw_ghost(self._cell_center(ox, oy, cell, position), int(cell * 0.72), RED, False, now)
        self._draw_pacman(self._cell_center(ox, oy, cell, maze.start), int(cell * 0.72), (1, 0), now)
        self._draw_exit(self._cell_center(ox, oy, cell, maze.exit), cell, True, now)

        tx = tools_panel.left + 18
        tw = tools_panel.width - 36
        self._text("BRUSH TOOLS", (tx, 135), 14, TEXT, True)
        for index, tool in enumerate(EditorTool, start=1):
            self._button(
                pygame.Rect(tx, 164 + (index - 1) * 46, tw, 38),
                f"{index}   {tool.value.upper()}",
                f"editor_tool:{tool.value}",
                CYAN if tool in {EditorTool.FLOOR, EditorTool.WALL} else PURPLE,
                active=editor.tool is tool,
                size=12,
            )
        stats_y = 164 + len(EditorTool) * 46 + 6
        stats = pygame.Rect(tx, stats_y, tw, 86)
        pygame.draw.rect(self.surface, (14, 24, 55), stats, border_radius=10)
        self._text("MAP CONTENT", (stats.left + 12, stats.top + 10), 10, MUTED, True)
        self._text(
            f"Pellets {len(maze.foods) + len(maze.power_foods)}   Ghosts {len(maze.ghost_starts)}   Weights {len(maze.terrain_costs)}",
            (stats.left + 12, stats.top + 31),
            11,
            TEXT,
        )
        self._wrapped_text(editor.status, pygame.Rect(stats.left + 12, stats.top + 51, stats.width - 24, 30), 10, YELLOW, 1)
        button_y = tools_panel.bottom - 118
        third = (tw - 12) // 3
        self._button(pygame.Rect(tx, button_y, third, 42), "BACK", "editor_back", MUTED, size=11)
        self._button(pygame.Rect(tx + third + 6, button_y, third, 42), "VALIDATE", "editor_validate", CYAN, size=10)
        self._button(pygame.Rect(tx + (third + 6) * 2, button_y, third, 42), "SAVE & PLAY", "editor_save", GREEN, size=9)
        self._text(
            "1–9 tools  •  V validate  •  S save  •  Esc back",
            (40, 870),
            12,
            MUTED,
        )

    def editor_cell_at(
        self,
        position: tuple[int, int],
        editor: MapEditor,
    ) -> Position | None:
        if not self.editor_grid_rect.collidepoint(position):
            return None
        cell = self.editor_grid_rect.width // editor.maze.width
        if cell <= 0:
            return None
        x = (position[0] - self.editor_grid_rect.left) // cell
        y = (position[1] - self.editor_grid_rect.top) // cell
        candidate = (int(x), int(y))
        if 0 <= candidate[0] < editor.maze.width and 0 <= candidate[1] < editor.maze.height:
            return candidate
        return None

    def draw_help_modal(self) -> None:
        self.buttons.clear()
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((1, 3, 12, 215))
        self.surface.blit(overlay, (0, 0))
        rect = pygame.Rect(300, 145, 840, 610)
        self._panel(rect, CYAN, 250, 24)
        self._text("HOW TO USE THE LAB", (rect.left + 38, rect.top + 32), 30, TEXT, True)
        sections = [
            ("1  Choose manual or AUTO", "Press 1–5 for a fixed search engine, or use the AI Workbench to enable explainable automatic selection."),
            ("2  Run or inspect one step", "Run AI starts automatic play. Step Once advances Pac-Man by one planned cell."),
            ("3  Read the visualization", "Cyan cells show explored states. The bright line is the selected route. Red auras add danger cost."),
            ("4  Open the AI Workbench", "Compare heuristics, run experiments, explain a route, replay a mission, export reports, or open Map Studio."),
            ("5  Complete the mission", "Collect every pellet, adapt to four ghost behaviors, then enter the unlocked green exit."),
        ]
        y = rect.top + 95
        for title, body in sections:
            self._text(title, (rect.left + 40, y), 18, CYAN, True)
            y = self._wrapped_text(
                body,
                pygame.Rect(rect.left + 40, y + 29, rect.width - 80, 50),
                15,
                MUTED,
                2,
            ) + 17
        self._button(
            pygame.Rect(rect.centerx - 100, rect.bottom - 67, 200, 44),
            "CLOSE  [ESC]",
            "close_modal",
            YELLOW,
        )

    def draw_end_modal(self, session: GameSession) -> None:
        self.buttons.clear()
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((1, 3, 12, 218))
        self.surface.blit(overlay, (0, 0))
        rect = pygame.Rect(385, 215, 670, 475)
        color = GREEN if session.won else RED
        self._panel(rect, color, 250, 26)
        title = "MISSION COMPLETE" if session.won else "MISSION FAILED"
        subtitle = "Every pellet secured and exit reached" if session.won else "The ghosts ended this run"
        self._text(title, (rect.centerx, rect.top + 52), 38, color, True, "center")
        self._text(subtitle, (rect.centerx, rect.top + 104), 17, MUTED, anchor="center")
        metrics = [
            ("Final score", str(session.score)),
            ("Travelled steps", str(session.metrics.travelled_steps)),
            ("Searches", str(session.metrics.searches)),
            ("Expanded nodes", str(session.metrics.expanded_nodes)),
        ]
        y = rect.top + 163
        for label, value in metrics:
            self._text(label, (rect.left + 90, y), 17, MUTED)
            self._text(value, (rect.right - 90, y), 20, TEXT, True, "topright")
            y += 46
        self._button(
            pygame.Rect(rect.left + 70, rect.bottom - 82, 250, 50),
            "RESTART",
            "reset",
            color,
        )
        self._button(
            pygame.Rect(rect.right - 320, rect.bottom - 82, 250, 50),
            "MAIN MENU",
            "menu",
            CYAN,
        )
