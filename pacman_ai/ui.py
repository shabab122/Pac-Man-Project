"""Pygame renderer for the neon pathfinding laboratory."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin
import random
from typing import Iterable

import pygame

from .models import Algorithm, Position, SearchResult
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
        self.maze_rect = pygame.Rect(30, 118, 868, 714)
        self.side_rect = pygame.Rect(920, 118, 490, 714)

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
        self._text("ARTIFICIAL INTELLIGENCE LAB", (72, 55), 18, CYAN, True)
        self._text("OPTIMIZED", (72, 118), 48, TEXT, True)
        self._text("PAC-MAN", (72, 170), 90, YELLOW, True)
        self._text("PATHFINDING LAB", (76, 268), 42, CYAN, True)
        self._wrapped_text(
            "Watch five classical AI search algorithms navigate a living maze, collect every data pellet, avoid moving ghosts, and reach the exit.",
            pygame.Rect(78, 335, 585, 110),
            22,
            (186, 204, 232),
            8,
        )

        feature_rect = pygame.Rect(72, 472, 602, 245)
        self._panel(feature_rect, PURPLE, 210)
        features = [
            ("01", "Five algorithms", "BFS, DFS, UCS, Dijkstra, and A*"),
            ("02", "Live search telemetry", "Path, expanded nodes, cost, frontier, and time"),
            ("03", "Dynamic simulation", "Moving ghosts, risk costs, power mode, and replanning"),
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
        self._text("AI ROUTE ENGINE", (1050, 192), 18, PINK, True, "center")
        self._text("SEARCH  /  PLAN  /  ADAPT", (1050, 603), 16, MUTED, True, "center")

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
        self._text("PAC-MAN", (35, 24), 32, YELLOW, True)
        self._text("PATHFINDING LAB", (218, 27), 27, TEXT, True)
        self._text(
            f"MAP  {session.map_index + 1:02d}  /  {session.maze.config.name.upper()}",
            (37, 69),
            14,
            session.maze.config.accent,
            True,
        )

        items = [
            ("SCORE", f"{session.score:04d}", YELLOW),
            ("PELLETS", f"{session.collected}/{session.total_collectibles}", CYAN),
            ("LIVES", "● " * session.lives or "0", PINK),
            ("ENGINE", session.algorithm.value.upper(), ALGORITHM_COLORS[session.algorithm.value]),
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

        # Soft danger rings make weighted search behavior visible.
        danger_layer = pygame.Surface(self.surface.get_size(), pygame.SRCALPHA)
        if not session.is_frightened(now):
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
        accent = ALGORITHM_COLORS[session.algorithm.value]

        self._text("SELECT SEARCH ENGINE", (x, 140), 15, TEXT, True)
        self._wrapped_text(
            session.algorithm.short_description,
            pygame.Rect(x, 166, width, 42),
            13,
            MUTED,
            2,
        )

        algorithms = list(Algorithm)
        button_width = (width - 10) // 2
        for index, algorithm in enumerate(algorithms):
            row = index // 2
            column = index % 2
            if index == 4:
                rect = pygame.Rect(x, 303, width, 42)
            else:
                rect = pygame.Rect(x + column * (button_width + 10), 207 + row * 48, button_width, 42)
            self._button(
                rect,
                f"{index + 1}  {algorithm.value.upper()}",
                f"algorithm:{algorithm.value}",
                ALGORITHM_COLORS[algorithm.value],
                active=session.algorithm == algorithm,
                size=14,
            )

        pygame.draw.line(self.surface, (55, 70, 110), (x, 365), (x + width, 365), 1)

        half = (width - 10) // 2
        run_label = "STOP AI" if session.running else "RUN AI"
        self._button(
            pygame.Rect(x, 382, half, 43),
            run_label,
            "toggle_run",
            GREEN if not session.running else RED,
            active=session.running,
        )
        self._button(pygame.Rect(x + half + 10, 382, half, 43), "STEP ONCE", "step", CYAN)
        self._button(pygame.Rect(x, 433, half, 43), "COMPARE", "compare", PURPLE)
        self._button(pygame.Rect(x + half + 10, 433, half, 43), "RESET", "reset", ORANGE)
        self._button(pygame.Rect(x, 484, half, 43), "NEXT MAP", "next_map", PINK)
        ghost_label = "GHOSTS: LIVE" if session.dynamic_ghosts else "GHOSTS: FROZEN"
        self._button(
            pygame.Rect(x + half + 10, 484, half, 43),
            ghost_label,
            "toggle_ghosts",
            RED if session.dynamic_ghosts else MUTED,
            active=session.dynamic_ghosts,
            size=13,
        )

        mission_rect = pygame.Rect(x, 546, width, 95)
        pygame.draw.rect(self.surface, (15, 26, 58), mission_rect, border_radius=12)
        pygame.draw.rect(self.surface, (*accent,), mission_rect, width=1, border_radius=12)
        self._text("MISSION PROGRESS", (mission_rect.left + 14, mission_rect.top + 12), 12, MUTED, True)
        self._text(
            f"{session.collected} of {session.total_collectibles} pellets secured",
            (mission_rect.left + 14, mission_rect.top + 34),
            15,
            TEXT,
            True,
        )
        track = pygame.Rect(mission_rect.left + 14, mission_rect.top + 64, mission_rect.width - 28, 12)
        pygame.draw.rect(self.surface, (30, 40, 72), track, border_radius=6)
        fill = track.copy()
        fill.width = max(0, int(track.width * session.progress))
        if fill.width:
            pygame.draw.rect(self.surface, accent, fill, border_radius=6)

        result = session.last_result
        metrics_rect = pygame.Rect(x, 653, width, 111)
        pygame.draw.rect(self.surface, (15, 26, 58), metrics_rect, border_radius=12)
        labels = (
            ("STEPS", str(result.steps) if result else "–"),
            ("COST", f"{result.path_cost:.0f}" if result else "–"),
            ("EXPANDED", str(result.expanded_nodes) if result else "–"),
            ("TIME", f"{result.elapsed_ms:.3f} ms" if result else "–"),
        )
        item_width = metrics_rect.width // 2
        for index, (label, value) in enumerate(labels):
            column = index % 2
            row = index // 2
            left = metrics_rect.left + column * item_width + 14
            top = metrics_rect.top + row * 50 + 10
            self._text(label, (left, top), 10, MUTED, True)
            self._text(value, (left, top + 18), 16, accent, True)

        self._text("SPEED", (x, 783), 11, MUTED, True)
        speed_x = x + 74
        for speed in (1, 2, 4):
            rect = pygame.Rect(speed_x, 773, 58, 32)
            self._button(
                rect,
                f"{speed}×",
                f"speed:{speed}",
                accent,
                active=session.speed == speed,
                size=13,
            )
            speed_x += 66

        frightened = session.is_frightened()
        mode = "POWER MODE" if frightened else ("PAUSED" if session.paused else session.status.upper())
        mode_color = BLUE if frightened else (ORANGE if session.paused else MUTED)
        self._text(mode[:42], (self.side_rect.right - 20, 816), 10, mode_color, True, "bottomright")

    def _draw_footer(self, session: GameSession) -> None:
        self._text(
            "ENTER run/stop     SPACE pause     S step     C compare     R reset     M map     H help",
            (35, 867),
            14,
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
            f"Same snapshot: start {session.player}  /  target {target}  /  weighted danger active",
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
            "Interpretation: fewer expanded nodes means less search work. UCS and Dijkstra normally match here because all movement costs are non-negative and the task uses one source and one target.",
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

    def draw_help_modal(self) -> None:
        self.buttons.clear()
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((1, 3, 12, 215))
        self.surface.blit(overlay, (0, 0))
        rect = pygame.Rect(300, 145, 840, 610)
        self._panel(rect, CYAN, 250, 24)
        self._text("HOW TO USE THE LAB", (rect.left + 38, rect.top + 32), 30, TEXT, True)
        sections = [
            ("1  Choose an algorithm", "Press 1–5 or click an algorithm. A* is the recommended default for weighted maps."),
            ("2  Run or inspect one step", "Run AI starts automatic play. Step Once advances Pac-Man by one planned cell."),
            ("3  Read the visualization", "Cyan cells show explored states. The bright line is the selected route. Red auras add danger cost."),
            ("4  Compare fairly", "Compare runs all five searches from the same current cell to the same target."),
            ("5  Complete the mission", "Collect every pellet, use power cores against ghosts, then enter the green exit gate."),
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
