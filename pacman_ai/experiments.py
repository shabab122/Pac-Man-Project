"""Repeatable algorithm experiments and CSV/PDF research reports."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import fmean

from .algorithms import manhattan
from .maze import Maze
from .models import Algorithm, HeuristicMode, Position, SearchResult
from .planner import compare_heuristics, plan_route


@dataclass(frozen=True, slots=True)
class ExperimentScenario:
    name: str
    start: Position
    goal: Position


@dataclass(frozen=True, slots=True)
class ExperimentRecord:
    scenario: str
    label: str
    algorithm: Algorithm
    heuristic_mode: HeuristicMode | None
    found: bool
    steps: int
    path_cost: float
    expanded_nodes: int
    frontier_peak: int
    elapsed_ms: float


@dataclass(frozen=True, slots=True)
class ExperimentSummary:
    label: str
    successful: int
    scenarios: int
    average_steps: float
    average_cost: float
    average_expanded: float
    average_frontier: float
    average_ms: float

    @property
    def success_rate(self) -> float:
        return self.successful / self.scenarios if self.scenarios else 0.0


@dataclass(slots=True)
class ExperimentReport:
    map_name: str
    created_at: str
    scenarios: list[ExperimentScenario]
    algorithm_records: list[ExperimentRecord]
    heuristic_records: list[ExperimentRecord]

    def summarize(self, records: list[ExperimentRecord]) -> list[ExperimentSummary]:
        labels = list(dict.fromkeys(record.label for record in records))
        summaries: list[ExperimentSummary] = []
        for label in labels:
            group = [record for record in records if record.label == label]
            found = [record for record in group if record.found]
            values = found or group
            summaries.append(
                ExperimentSummary(
                    label=label,
                    successful=len(found),
                    scenarios=len(group),
                    average_steps=fmean(record.steps for record in values),
                    average_cost=fmean(record.path_cost for record in values),
                    average_expanded=fmean(record.expanded_nodes for record in values),
                    average_frontier=fmean(record.frontier_peak for record in values),
                    average_ms=fmean(record.elapsed_ms for record in values),
                )
            )
        return summaries

    @property
    def algorithm_summaries(self) -> list[ExperimentSummary]:
        return self.summarize(self.algorithm_records)

    @property
    def heuristic_summaries(self) -> list[ExperimentSummary]:
        return self.summarize(self.heuristic_records)


def build_scenarios(
    maze: Maze,
    start: Position,
    targets: set[Position],
    exit_position: Position,
    limit: int = 5,
) -> list[ExperimentScenario]:
    """Choose deterministic near-to-far goals that reveal search trade-offs."""

    if limit < 1:
        raise ValueError("limit must be positive")
    ordered = sorted(
        {target for target in targets | {exit_position} if target != start},
        key=lambda target: (manhattan(start, target), target[1], target[0]),
    )
    if not ordered:
        return []
    if len(ordered) <= limit:
        selected = ordered
    else:
        indices = {
            round(index * (len(ordered) - 1) / (limit - 1))
            for index in range(limit)
        } if limit > 1 else {len(ordered) - 1}
        selected = [ordered[index] for index in sorted(indices)]

    scenarios: list[ExperimentScenario] = []
    for index, goal in enumerate(selected, start=1):
        kind = "Exit" if goal == exit_position else f"Target {index}"
        scenarios.append(ExperimentScenario(kind, start, goal))
    return scenarios


def _record(
    scenario: ExperimentScenario,
    label: str,
    result: SearchResult,
    elapsed_ms: float,
) -> ExperimentRecord:
    return ExperimentRecord(
        scenario=scenario.name,
        label=label,
        algorithm=result.algorithm,
        heuristic_mode=result.heuristic_mode,
        found=result.found,
        steps=result.steps,
        path_cost=result.path_cost,
        expanded_nodes=result.expanded_nodes,
        frontier_peak=result.frontier_peak,
        elapsed_ms=elapsed_ms,
    )


def run_experiment(
    maze: Maze,
    start: Position,
    targets: set[Position],
    exit_position: Position,
    ghost_positions: tuple[Position, ...] = (),
    frightened: bool = False,
    heuristic_mode: HeuristicMode = HeuristicMode.MANHATTAN,
    timing_repeats: int = 3,
) -> ExperimentReport:
    """Benchmark all algorithms and A* heuristics on fixed scenarios."""

    if timing_repeats < 1:
        raise ValueError("timing_repeats must be positive")
    scenarios = build_scenarios(maze, start, targets, exit_position)
    algorithm_records: list[ExperimentRecord] = []
    heuristic_records: list[ExperimentRecord] = []

    for scenario in scenarios:
        for algorithm in Algorithm:
            runs = [
                plan_route(
                    algorithm,
                    maze,
                    scenario.start,
                    scenario.goal,
                    ghost_positions,
                    frightened,
                    heuristic_mode,
                )
                for _ in range(timing_repeats)
            ]
            result = runs[0]
            elapsed = fmean(item.elapsed_ms for item in runs)
            algorithm_records.append(_record(scenario, algorithm.value, result, elapsed))

        heuristic_runs = compare_heuristics(
            maze,
            scenario.start,
            scenario.goal,
            ghost_positions,
            frightened,
        )
        for result in heuristic_runs:
            mode = result.heuristic_mode or HeuristicMode.MANHATTAN
            heuristic_records.append(_record(scenario, mode.value, result, result.elapsed_ms))

    return ExperimentReport(
        map_name=maze.config.name,
        created_at=datetime.now(timezone.utc).isoformat(),
        scenarios=scenarios,
        algorithm_records=algorithm_records,
        heuristic_records=heuristic_records,
    )


def export_csv(report: ExperimentReport, path: str | Path) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Adaptive Pac-Man AI Experiment"])
        writer.writerow(["Map", report.map_name])
        writer.writerow(["Created (UTC)", report.created_at])
        writer.writerow([])
        writer.writerow(
            [
                "category",
                "scenario",
                "label",
                "algorithm",
                "heuristic",
                "found",
                "steps",
                "path_cost",
                "expanded_nodes",
                "frontier_peak",
                "elapsed_ms",
            ]
        )
        for category, records in (
            ("algorithm", report.algorithm_records),
            ("heuristic", report.heuristic_records),
        ):
            for record in records:
                writer.writerow(
                    [
                        category,
                        record.scenario,
                        record.label,
                        record.algorithm.value,
                        record.heuristic_mode.value if record.heuristic_mode else "",
                        record.found,
                        record.steps,
                        f"{record.path_cost:.3f}",
                        record.expanded_nodes,
                        record.frontier_peak,
                        f"{record.elapsed_ms:.6f}",
                    ]
                )
    return destination


def export_pdf(report: ExperimentReport, path: str | Path) -> Path:
    """Export a compact, presentation-ready PDF with summary tables."""

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover - exercised only on incomplete installs
        raise RuntimeError("PDF export requires reportlab from requirements.txt") from exc

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    regular_font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    bold_font = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
    font_name = "Helvetica"
    bold_name = "Helvetica-Bold"
    if regular_font.exists() and bold_font.exists():
        pdfmetrics.registerFont(TTFont("PacmanSans", str(regular_font)))
        pdfmetrics.registerFont(TTFont("PacmanSansBold", str(bold_font)))
        font_name = "PacmanSans"
        bold_name = "PacmanSansBold"
    page_width, page_height = landscape(A4)
    pdf = canvas.Canvas(str(destination), pagesize=(page_width, page_height))
    pdf.setTitle("Adaptive Pac-Man AI Experiment Report")
    pdf.setAuthor("Adaptive Pac-Man AI Pathfinding Laboratory")
    dark = colors.HexColor("#111936")
    ink = colors.HexColor("#253452")
    grid = colors.HexColor("#a9b7d5")
    pale = colors.HexColor("#eef2ff")
    accent = colors.HexColor("#ff4fb0")

    pdf.setFillColor(dark)
    pdf.setFont(bold_name, 21)
    pdf.drawString(42, page_height - 48, "Adaptive Pac-Man AI - Experiment Report")
    pdf.setFillColor(ink)
    pdf.setFont(font_name, 9.5)
    pdf.drawString(
        42,
        page_height - 69,
        f"Map: {report.map_name}    Scenarios: {len(report.scenarios)}    Generated: {report.created_at}",
    )

    x0 = 42.0
    widths = [145.0, 74.0, 82.0, 82.0, 103.0, 96.0, 88.0]
    row_height = 25.0

    def draw_table(
        title: str,
        summaries: list[ExperimentSummary],
        top: float,
    ) -> float:
        headers = (title, "Success", "Avg steps", "Avg cost", "Avg expanded", "Avg frontier", "Avg ms")
        total_width = sum(widths)
        pdf.setFillColor(dark)
        pdf.rect(x0, top - row_height, total_width, row_height, fill=1, stroke=0)
        cursor = x0
        pdf.setFillColor(colors.white)
        pdf.setFont(bold_name, 8.5)
        for index, (header, width) in enumerate(zip(headers, widths)):
            if index == 0:
                pdf.drawString(cursor + 8, top - 17, header)
            else:
                pdf.drawCentredString(cursor + width / 2, top - 17, header)
            cursor += width

        y = top - row_height
        for row_index, item in enumerate(summaries):
            y -= row_height
            pdf.setFillColor(colors.white if row_index % 2 == 0 else pale)
            pdf.rect(x0, y, total_width, row_height, fill=1, stroke=0)
            values = (
                item.label,
                f"{item.successful}/{item.scenarios}",
                f"{item.average_steps:.1f}",
                f"{item.average_cost:.1f}",
                f"{item.average_expanded:.1f}",
                f"{item.average_frontier:.1f}",
                f"{item.average_ms:.4f}",
            )
            cursor = x0
            for index, (value, width) in enumerate(zip(values, widths)):
                pdf.setFillColor(accent if index == 0 else ink)
                pdf.setFont(bold_name if index == 0 else font_name, 8.5)
                if index == 0:
                    pdf.drawString(cursor + 8, y + 8, value)
                else:
                    pdf.drawCentredString(cursor + width / 2, y + 8, value)
                cursor += width

        table_bottom = y
        pdf.setStrokeColor(grid)
        pdf.setLineWidth(0.45)
        cursor = x0
        for width in widths:
            pdf.line(cursor, table_bottom, cursor, top)
            cursor += width
        pdf.line(cursor, table_bottom, cursor, top)
        for line_index in range(len(summaries) + 2):
            line_y = top - line_index * row_height
            pdf.line(x0, line_y, x0 + total_width, line_y)
        return table_bottom

    first_bottom = draw_table("Algorithm", report.algorithm_summaries, page_height - 105)
    second_bottom = draw_table(
        "A* heuristic",
        report.heuristic_summaries,
        first_bottom - 28,
    )

    note = (
        "Interpretation: expanded nodes measure search work; path cost includes terrain and active "
        "ghost-danger penalties. Weighted A* may reduce search effort, but unlike Manhattan and "
        "Euclidean A*, it does not guarantee an optimal path. Timing is hardware-dependent; compare "
        "it together with deterministic steps, cost, frontier, and expanded-node counts."
    )
    words = note.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and pdf.stringWidth(candidate, font_name, 8.5) > sum(widths):
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    pdf.setFillColor(ink)
    pdf.setFont(font_name, 8.5)
    text_y = second_bottom - 28
    for line in lines:
        pdf.drawString(x0, text_y, line)
        text_y -= 12
    pdf.setFillColor(colors.HexColor("#66728e"))
    pdf.setFont(font_name, 7.5)
    pdf.drawRightString(page_width - 42, 24, "Generated locally - controlled scenario evidence")
    pdf.save()
    return destination
