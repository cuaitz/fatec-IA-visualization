"""Owns and renders a tile-based maze, and runs the step-by-step pathfinding \
algorithms (Dijkstra, A*, Greedy A*) over it."""

import heapq
import math
import random
import time
from dataclasses import dataclass, field

import pygame

HEURISTIC_BIAS = 5

WALL_CELL_COLOR = "#232329"
FLOOR_CELL_COLOR = "#6e6e7f"
CELL_PADDING = 2

# Fraction of cells turned into walls; tweak to taste.
WALL_DENSITY = 0.25

CELL_START_COLOR = "#4caf50"
CELL_END_COLOR = "#e05353"
CELL_VISITED_COLOR = "#3d6da6"
CELL_FRONTIER_COLOR = "#d1a23a"
CELL_PATH_COLOR = "#7ed957"


@dataclass
class AlgorithmStep:
    """A single snapshot of a pathfinding run, used to animate/scrub through it."""

    current: int | None
    visited: set[int]
    frontier: set[int]
    path: list[int]
    costs: dict[int, float] = field(default_factory=dict)


class MazeArea:
    """Holds the generated maze grid and draws it within its bounds."""

    def __init__(self, bounds: pygame.Rect) -> None:
        self.bounds = bounds
        self.size = 0
        self.cell_size = 0
        self.walls: set[int] = set()

        self.algorithm = "dijkstra"
        self.start_cell: int | None = None
        self.end_cell: int | None = None
        self.steps: list[AlgorithmStep] = []
        self.step_index = -1
        self.is_playing = False
        self._frame_counter = 0
        self.show_costs = False
        self._cost_surface: pygame.Surface | None = None
        self._cost_cache_key: tuple | None = None

    def set_show_costs(self, show_costs: bool) -> None:
        self.show_costs = show_costs

    def generate(self, size: int) -> None:
        """Blocks off a fraction of a `size` x `size` grid as walls and sends the start/end \
        to opposite corners (as far apart as two cells can be on a square grid)."""

        self.size = size
        self.cell_size = min(self.bounds.width, self.bounds.height) // size
        self.start_cell = 0
        self.end_cell = size * size - 1
        self.walls = self._carve_maze(size, self.start_cell, self.end_cell)
        self._reset_run()

    def _carve_maze(self, size: int, start: int, end: int) -> set[int]:
        """Randomly blocks off roughly `WALL_DENSITY` of the cells as walls, rejecting any \
        wall that would cut off part of the grid from the start cell (keeping the whole \
        maze, including the end cell, reachable in one connected region)."""

        cell_count = size * size
        wall_target = int(cell_count * WALL_DENSITY)
        candidates = list(range(cell_count))
        random.shuffle(candidates)

        walls: set[int] = set()
        placed = 0

        for cell in candidates:
            if placed >= wall_target:
                break
            if cell == start or cell == end:
                continue

            walls.add(cell)
            if self._is_fully_connected(walls, size, start):
                placed += 1
            else:
                walls.remove(cell)

        return walls

    def _is_fully_connected(self, walls: set[int], size: int, start: int) -> bool:
        """Checks that every non-wall cell is still reachable from the start cell, via BFS."""

        floor_count = size * size - len(walls)
        visited = {start}
        queue = [start]

        while queue:
            cell = queue.pop()
            for neighbor in self._neighbors(cell, size):
                if neighbor not in walls and neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return len(visited) == floor_count

    def _neighbors(self, cell: int, size: int) -> list[int]:
        row, col = divmod(cell, size)
        neighbors = []

        if row > 0:
            neighbors.append(cell - size)
        if row < size - 1:
            neighbors.append(cell + size)
        if col > 0:
            neighbors.append(cell - 1)
        if col < size - 1:
            neighbors.append(cell + 1)

        return neighbors

    def handle_click(self, position: tuple[int, int], button: int) -> None:
        """Right-click places a wall, left-click removes one, at the cell under the cursor."""

        self._paint(position, button)

    def handle_drag(self, position: tuple[int, int], button: int) -> None:
        """Continues placing/removing walls while a mouse button is held and dragged."""

        self._paint(position, button)

    def _paint(self, position: tuple[int, int], button: int) -> None:
        if button not in (1, 3):
            return

        cell = self._cell_at(position)
        if cell is None or cell == self.start_cell or cell == self.end_cell:
            return

        if button == 3:
            changed = cell not in self.walls
            self.walls.add(cell)
        else:
            changed = cell in self.walls
            self.walls.discard(cell)

        if changed:
            self._reset_run()

    def _cell_at(self, position: tuple[int, int]) -> int | None:
        if not self.size or not self.bounds.collidepoint(position):
            return None

        col = (position[0] - self.bounds.left) // self.cell_size
        row = (position[1] - self.bounds.top) // self.cell_size

        if not (0 <= row < self.size and 0 <= col < self.size):
            return None

        return row * self.size + col

    def set_algorithm(self, algorithm: str) -> None:
        self.algorithm = algorithm
        self._reset_run()

    def start(self) -> None:
        """Starts (or resumes) auto-playing through the current algorithm's steps."""

        if not self._ensure_run():
            return

        self.is_playing = True

    def stop(self) -> None:
        self.is_playing = False

    def restart(self) -> None:
        """Rewinds the current run back to its first step and pauses playback."""

        self.is_playing = False
        self._frame_counter = 0

        if self.steps:
            self.step_index = 0
        else:
            self._ensure_run()

    def step(self, delta: int) -> None:
        """Manually moves forward/backward through the algorithm's steps."""

        if not self._ensure_run():
            return

        self.is_playing = False
        self.step_index = max(0, min(self.step_index + delta, len(self.steps) - 1))

    def update(self, step_duration: int) -> None:
        """Advances the auto-play, spending `step_duration` frames on each step."""

        if not self.is_playing:
            return

        self._frame_counter += 1
        if self._frame_counter < max(1, step_duration):
            return

        self._frame_counter = 0
        if self.step_index >= len(self.steps) - 1:
            self.is_playing = False
            return

        self.step_index += 1

    def _ensure_run(self) -> bool:
        """Makes sure `self.steps` holds a computed run for the current start/end cells, \
        computing one now if needed. Returns whether a run is available."""

        if self.start_cell is None or self.end_cell is None:
            return False

        if not self.steps:
            self._compute_steps()

        return bool(self.steps)

    def _reset_run(self) -> None:
        self.steps = []
        self.step_index = -1
        self.is_playing = False
        self._frame_counter = 0

    def _compute_steps(self) -> None:
        assert self.start_cell is not None and self.end_cell is not None, "start/end must be set"

        start_time = time.perf_counter()
        adjacency = self._build_adjacency()

        if self.algorithm == "a_star":
            self.steps = self._run_best_first(adjacency, self.start_cell, self.end_cell, greedy=False)
        elif self.algorithm == "greedy":
            self.steps = self._run_best_first(adjacency, self.start_cell, self.end_cell, greedy=True)
        else:
            self.steps = self._run_dijkstra(adjacency, self.start_cell, self.end_cell)
        elapsed_ms = (time.perf_counter() - start_time) * 1000

        path = self.steps[-1].path
        if path:
            print(f"{self.algorithm}: path found, {len(path)} cells ({elapsed_ms:.2f} ms)")
        else:
            print(f"{self.algorithm}: no path found ({elapsed_ms:.2f} ms)")

        self.step_index = 0

    def _build_adjacency(self) -> dict[int, list[int]]:
        adjacency: dict[int, list[int]] = {}

        for cell in range(self.size * self.size):
            if cell not in self.walls:
                adjacency[cell] = [n for n in self._neighbors(cell, self.size) if n not in self.walls]

        return adjacency

    def _heuristic(self, cell: int, end: int) -> int:
        # Manhattan distance: an admissible lower bound since moves only go to adjacent cells.
        row, col = divmod(cell, self.size)
        end_row, end_col = divmod(end, self.size)
        return abs(row - end_row) + abs(col - end_col)

    def _run_dijkstra(
        self, adjacency: dict[int, list[int]], start: int, end: int
    ) -> list[AlgorithmStep]:
        distances = {cell: math.inf for cell in adjacency}
        distances[start] = 0
        previous: dict[int, int] = {}
        visited: set[int] = set()
        heap: list[tuple[int, int]] = [(0, start)]
        steps: list[AlgorithmStep] = []

        while heap:
            distance, cell = heapq.heappop(heap)
            if cell in visited:
                continue
            visited.add(cell)

            known_costs = {
                known_cell: value
                for known_cell, value in distances.items()
                if value != math.inf
            }
            frontier = {n for _, n in heap if n not in visited}
            steps.append(
                AlgorithmStep(
                    current=cell,
                    visited=set(visited),
                    frontier=frontier,
                    path=[],
                    costs=known_costs,
                )
            )

            if cell == end:
                break

            for neighbor in adjacency[cell]:
                if neighbor in visited:
                    continue

                new_distance = distance + 1
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    previous[neighbor] = cell
                    heapq.heappush(heap, (new_distance, neighbor))

        return self._finalize_steps(steps, previous, start, end)

    def _run_best_first(
        self, adjacency: dict[int, list[int]], start: int, end: int, greedy: bool
    ) -> list[AlgorithmStep]:
        """Runs A* (`greedy=False`) or greedy best-first search (`greedy=True`, which \
        picks the next cell by heuristic alone, ignoring the cost already spent to reach it)."""

        distances = {cell: math.inf for cell in adjacency}
        distances[start] = 0
        previous: dict[int, int] = {}
        visited: set[int] = set()
        heap: list[tuple[int, int, int]] = [(self._heuristic(start, end), 0, start)]
        steps: list[AlgorithmStep] = []

        while heap:
            _, distance, cell = heapq.heappop(heap)
            if cell in visited:
                continue
            visited.add(cell)

            known_costs = {
                known_cell: value
                for known_cell, value in distances.items()
                if value != math.inf
            }
            frontier = {n for _, _, n in heap if n not in visited}
            steps.append(
                AlgorithmStep(
                    current=cell,
                    visited=set(visited),
                    frontier=frontier,
                    path=[],
                    costs=known_costs,
                )
            )

            if cell == end:
                break

            for neighbor in adjacency[cell]:
                if neighbor in visited:
                    continue

                new_distance = distance + 1
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    previous[neighbor] = cell
                    heuristic = self._heuristic(neighbor, end)
                    priority = (
                        new_distance + heuristic * HEURISTIC_BIAS
                        if greedy
                        else new_distance + heuristic
                    )
                    heapq.heappush(heap, (priority, new_distance, neighbor))

        return self._finalize_steps(steps, previous, start, end)

    def _finalize_steps(
        self,
        steps: list[AlgorithmStep],
        previous: dict[int, int],
        start: int,
        end: int,
    ) -> list[AlgorithmStep]:
        """Attaches the reconstructed path to the last step, so it only appears once \
        the algorithm has actually reached (or given up looking for) the end cell."""

        path = self._reconstruct_path(previous, start, end)

        if not steps:
            return [AlgorithmStep(current=None, visited=set(), frontier=set(), path=path, costs={})]

        steps[-1] = AlgorithmStep(
            current=steps[-1].current,
            visited=steps[-1].visited,
            frontier=steps[-1].frontier,
            path=path,
            costs=steps[-1].costs,
        )
        return steps

    def _reconstruct_path(self, previous: dict[int, int], start: int, end: int) -> list[int]:
        if end != start and end not in previous:
            return []

        path = [end]
        while path[-1] != start:
            path.append(previous[path[-1]])
        path.reverse()

        return path

    def render(self, screen: pygame.Surface) -> None:
        if not self.size:
            return

        current_step = self.steps[self.step_index] if 0 <= self.step_index < len(self.steps) else None

        for cell in range(self.size * self.size):
            row, col = divmod(cell, self.size)

            if cell in self.walls:
                self._draw_tile(screen, row, col, WALL_CELL_COLOR, padding=0)
            else:
                color = self._cell_color(cell, current_step) or FLOOR_CELL_COLOR
                self._draw_tile(screen, row, col, color)

        self._ensure_cost_surface(current_step)
        if self._cost_surface is not None:
            screen.blit(self._cost_surface, self.bounds.topleft)

    def _ensure_cost_surface(self, current_step: AlgorithmStep | None) -> None:
        """Rebuilds the cached cost-label overlay only when the step, grid size or toggle \
        actually change, instead of re-rendering every tile's label every frame."""

        cache_key = (id(current_step), self.show_costs, self.cell_size, self.size)
        if cache_key == self._cost_cache_key:
            return

        self._cost_cache_key = cache_key
        surface = pygame.Surface(self.bounds.size, pygame.SRCALPHA)

        if self.show_costs and current_step is not None:
            font = pygame.font.SysFont("arial", max(10, self.cell_size // 5))
            for cell in range(self.size * self.size):
                cost = self._display_cost(cell, current_step)
                if cost is None:
                    continue

                row, col = divmod(cell, self.size)
                text = font.render(str(int(cost)), True, (255, 255, 255))
                center = (
                    col * self.cell_size + self.cell_size // 2,
                    row * self.cell_size + self.cell_size // 2,
                )
                surface.blit(text, text.get_rect(center=center))

        self._cost_surface = surface

    def _display_cost(self, cell: int, current_step: AlgorithmStep | None) -> float | None:
        if current_step is None or cell not in current_step.costs:
            return None

        cost = current_step.costs[cell]
        if self.algorithm in ("a_star", "greedy") and self.end_cell is not None:
            heuristic = self._heuristic(cell, self.end_cell)
            if self.algorithm == "greedy":
                return cost + heuristic * HEURISTIC_BIAS
            return cost + heuristic

        return cost

    def _draw_tile(
        self, screen: pygame.Surface, row: int, col: int, color: str, padding: int = CELL_PADDING
    ) -> None:
        rect = pygame.Rect(
            self.bounds.left + col * self.cell_size + padding,
            self.bounds.top + row * self.cell_size + padding,
            self.cell_size - 2 * padding,
            self.cell_size - 2 * padding,
        )
        pygame.draw.rect(screen, color, rect)

    def _cell_color(self, cell: int, current_step: AlgorithmStep | None) -> str | None:
        if current_step is not None and cell in current_step.path:
            return CELL_PATH_COLOR
        if cell == self.start_cell:
            return CELL_START_COLOR
        if cell == self.end_cell:
            return CELL_END_COLOR
        if current_step is not None:
            if cell in current_step.visited:
                return CELL_VISITED_COLOR
            if cell in current_step.frontier:
                return CELL_FRONTIER_COLOR

        return None
