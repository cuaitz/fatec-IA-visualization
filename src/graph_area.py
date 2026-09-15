"""Owns and renders the nodes and edges placed within the graph area, and runs the \
step-by-step pathfinding algorithms (Dijkstra, A*) over them."""

import heapq
import itertools
import math
import random
import time
from dataclasses import dataclass, replace

import pygame

NODE_RADIUS = 15
NODE_MARGIN = NODE_RADIUS + 10
MIN_NODE_DISTANCE = NODE_RADIUS * 3
MAX_PLACEMENT_ATTEMPTS = 500
NODE_CLICK_RADIUS = NODE_RADIUS * 1.5

NODE_COLOR = "#686898"
NODE_BORDER_COLOR = "#eeeeee"
NODE_START_COLOR = "#4caf50"
NODE_END_COLOR = "#e05353"
NODE_VISITED_COLOR = "#e8470d"
NODE_FRONTIER_COLOR = "#d1a23a"
NODE_PATH_COLOR = "#7ed957"

EDGE_COLOR = "#4a4a5a"
PATH_EDGE_COLOR = "#7ed957"
EDGE_WEIGHT_COLOR = "#cfcfcf"
EDGE_WEIGHT_FONT_SIZE = 36

COST_LABEL_COLOR = "#ffffff"
COST_LABEL_FONT_SIZE = 16

# Divides an edge's on-screen length to get its weight; tweak to taste.
EDGE_WEIGHT_FACTOR = 40

# How much larger the pool of nearby candidate edges is than what's actually
# needed, before randomly sampling from it. Higher values favor locality less.
LOCAL_EDGE_POOL_FACTOR = 3


@dataclass
class AlgorithmStep:
    """A single snapshot of a pathfinding run, used to animate/scrub through it."""

    current: int | None
    visited: set[int]
    frontier: set[int]
    path: list[int]
    previous: dict[int, int]
    distances: dict[int, float]


class GraphArea:
    """Holds the generated nodes/edges and draws them within its bounds."""

    def __init__(self, bounds: pygame.Rect) -> None:
        self.bounds = bounds
        self.nodes: list[tuple[int, int]] = []
        self.edges: list[tuple[int, int]] = []
        self.weight_font = pygame.font.SysFont(None, EDGE_WEIGHT_FONT_SIZE)
        self.cost_font = pygame.font.SysFont(None, COST_LABEL_FONT_SIZE)

        self.algorithm = "dijkstra"
        self.start_node: int | None = None
        self.end_node: int | None = None
        self.steps: list[AlgorithmStep] = []
        self.step_index = -1
        self.is_playing = False
        self.show_costs = False
        self._frame_counter = 0

    def generate(self, node_count: int, edge_count: int) -> None:
        """Scatters `node_count` well-separated nodes, then connects `edge_count` pairs \
        favoring nearby nodes, for a web-like look."""

        self.nodes = self._generate_nodes(node_count)
        self.edges = self._generate_edges(edge_count)
        self.start_node, self.end_node = self._farthest_pair()
        self._reset_run()

    def _farthest_pair(self) -> tuple[int | None, int | None]:
        """Picks the two nodes with the largest distance between them, so the start and \
        end points aren't right next to each other."""

        if len(self.nodes) < 2:
            return (0, None) if self.nodes else (None, None)

        return max(
            itertools.combinations(range(len(self.nodes)), 2),
            key=lambda pair: math.dist(self.nodes[pair[0]], self.nodes[pair[1]]),
        )

    def _generate_nodes(self, node_count: int) -> list[tuple[int, int]]:
        """Places nodes at random positions, rejecting candidates that land too close to
        an existing node so that edges between them stay visually distinguishable."""

        min_x = self.bounds.left + NODE_MARGIN
        max_x = self.bounds.right - NODE_MARGIN
        min_y = self.bounds.top + NODE_MARGIN
        max_y = self.bounds.bottom - NODE_MARGIN

        nodes: list[tuple[int, int]] = []

        for _ in range(node_count):
            best_candidate = (random.randint(min_x, max_x), random.randint(min_y, max_y))
            best_distance = -1.0

            for _ in range(MAX_PLACEMENT_ATTEMPTS):
                candidate = (random.randint(min_x, max_x), random.randint(min_y, max_y))
                closest_distance = min(
                    (math.dist(candidate, other) for other in nodes),
                    default=math.inf,
                )

                if closest_distance >= MIN_NODE_DISTANCE:
                    best_candidate = candidate
                    break

                # Keeps the least-bad candidate in case every attempt is too close
                if closest_distance > best_distance:
                    best_distance = closest_distance
                    best_candidate = candidate

            nodes.append(best_candidate)

        return nodes

    def _generate_edges(self, edge_count: int) -> list[tuple[int, int]]:
        """Builds `edge_count` unique edges biased towards connecting nearby nodes. Starts \
        from a Euclidean minimum spanning tree, which already touches every node using only \
        its closest connections (no isolated vertices), then fills the rest by randomly \
        sampling from a pool of the shortest remaining candidate edges."""

        node_count = len(self.nodes)

        if node_count < 2:
            return []

        max_edges = node_count * (node_count - 1) // 2
        actual_edge_count = max(min(edge_count, max_edges), node_count - 1)

        distances = {
            edge: math.dist(self.nodes[edge[0]], self.nodes[edge[1]])
            for edge in itertools.combinations(range(node_count), 2)
        }

        edges = self._minimum_spanning_tree(node_count, distances)
        used_edges = set(edges)

        remaining_edges = sorted(
            (edge for edge in distances if edge not in used_edges),
            key=lambda edge: distances[edge],
        )

        extra_needed = actual_edge_count - len(edges)
        edges.extend(self._pick_nearby_edges(remaining_edges, extra_needed))

        return edges

    def _minimum_spanning_tree(
        self, node_count: int, distances: dict[tuple[int, int], float]
    ) -> list[tuple[int, int]]:
        """Connects every node using Prim's algorithm, so the tree's edges are always \
        the shortest ones needed to reach each new node."""

        in_tree = [False] * node_count
        in_tree[0] = True
        tree_edges: list[tuple[int, int]] = []

        for _ in range(node_count - 1):
            best_edge: tuple[int, int] | None = None
            best_distance = math.inf

            for u in range(node_count):
                if not in_tree[u]:
                    continue

                for v in range(node_count):
                    if in_tree[v]:
                        continue

                    edge = (u, v) if u < v else (v, u)
                    if distances[edge] < best_distance:
                        best_distance = distances[edge]
                        best_edge = edge

            assert best_edge is not None, "There must be a node left outside the tree"
            tree_edges.append(best_edge)
            in_tree[best_edge[0]] = True
            in_tree[best_edge[1]] = True

        return tree_edges

    def _pick_nearby_edges(
        self, edges_by_distance: list[tuple[int, int]], count: int
    ) -> list[tuple[int, int]]:
        """Randomly samples `count` edges out of a pool made of the shortest candidates in \
        `edges_by_distance`, keeping the result mostly local while still varying between runs."""

        if count <= 0:
            return []

        pool_size = min(len(edges_by_distance), count * LOCAL_EDGE_POOL_FACTOR)
        pool = edges_by_distance[:pool_size]

        return random.sample(pool, min(count, len(pool)))

    def handle_click(self, position: tuple[int, int], button: int) -> None:
        """Left-click sets the start node, right-click sets the end node, for the next run."""

        node_index = self._find_node_at(position)
        if node_index is None:
            return

        if button == 1:
            self.start_node = node_index
        elif button == 3:
            self.end_node = node_index
        else:
            return

        self._reset_run()

    def _find_node_at(self, position: tuple[int, int]) -> int | None:
        for index, node_position in enumerate(self.nodes):
            if math.dist(position, node_position) <= NODE_CLICK_RADIUS:
                return index

        return None

    def set_algorithm(self, algorithm: str) -> None:
        self.algorithm = algorithm
        self._reset_run()

    def set_show_costs(self, show_costs: bool) -> None:
        self.show_costs = show_costs

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
        """Makes sure `self.steps` holds a computed run for the current start/end nodes, \
        computing one now if needed. Returns whether a run is available."""

        if self.start_node is None or self.end_node is None:
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
        assert self.start_node is not None and self.end_node is not None, "start/end must be set"

        adjacency = self._build_adjacency()

        start_time = time.perf_counter()

        if self.algorithm == "a_star":
            self.steps = self._run_a_star(adjacency, self.start_node, self.end_node)
        elif self.algorithm == "greedy":
            self.steps = self._run_a_star(adjacency, self.start_node, self.end_node, heuristic_factor=1)
        else:
            self.steps = self._run_dijkstra(adjacency, self.start_node, self.end_node)

        elapsed_ms = (time.perf_counter() - start_time) * 1000
        self.step_index = 0
        self._report_result(elapsed_ms)

    def _report_result(self, elapsed_ms: float) -> None:
        final_step = self.steps[-1]

        if not final_step.path:
            print(f"{self.algorithm}: no path found ({elapsed_ms:.2f} ms)")
            return

        cost = final_step.distances.get(self.end_node)
        if cost is None:
            cost = sum(self._edge_weight(a, b) for a, b in zip(final_step.path, final_step.path[1:]))

        print(f"{self.algorithm}: path found, {round(cost, 1)} units ({elapsed_ms:.2f} ms)")

    def _build_adjacency(self) -> dict[int, list[tuple[int, int]]]:
        adjacency: dict[int, list[tuple[int, int]]] = {index: [] for index in range(len(self.nodes))}

        for start_index, end_index in self.edges:
            weight = self._edge_weight(start_index, end_index)
            adjacency[start_index].append((end_index, weight))
            adjacency[end_index].append((start_index, weight))

        return adjacency

    def _edge_weight(self, start_index  : int, end_index: int) -> int:
        return math.ceil(math.dist(self.nodes[start_index], self.nodes[end_index]) / EDGE_WEIGHT_FACTOR)

    def _heuristic(self, node_index: int, end_index: int, factor: float = EDGE_WEIGHT_FACTOR) -> float:
        return math.dist(self.nodes[node_index], self.nodes[end_index]) / factor    

    def _run_dijkstra(
        self, adjacency: dict[int, list[tuple[int, int]]], start: int, end: int
    ) -> list[AlgorithmStep]:
        distances = {node: math.inf for node in adjacency}
        distances[start] = 0
        previous: dict[int, int] = {}
        visited: set[int] = set()
        heap: list[tuple[float, int]] = [(0, start)]
        steps: list[AlgorithmStep] = []

        while heap:
            distance, node = heapq.heappop(heap)
            if node in visited:
                continue
            visited.add(node)

            reached_end = node == end
            if not reached_end:
                for neighbor, weight in adjacency[node]:
                    if neighbor in visited:
                        continue

                    new_distance = distance + weight
                    if new_distance < distances[neighbor]:
                        distances[neighbor] = new_distance
                        previous[neighbor] = node
                        heapq.heappush(heap, (new_distance, neighbor))

            # Snapshot after expanding, so newly discovered frontier edges show up now.
            frontier = {n for _, n in heap if n not in visited}
            reached = {n: d for n, d in distances.items() if d < math.inf}
            steps.append(
                AlgorithmStep(
                    current=node,
                    visited=set(visited),
                    frontier=frontier,
                    path=[],
                    previous=dict(previous),
                    distances=reached,
                )
            )

            if reached_end:
                break

        return self._finalize_steps(steps, previous, start, end)

    def _run_a_star(
        self,
        adjacency: dict[int, list[tuple[int, int]]],
        start: int,
        end: int,
        heuristic_factor: float = EDGE_WEIGHT_FACTOR,
    ) -> list[AlgorithmStep]:
        distances = {node: math.inf for node in adjacency}
        distances[start] = 0
        previous: dict[int, int] = {}
        visited: set[int] = set()
        heap: list[tuple[float, float, int]] = [(self._heuristic(start, end, heuristic_factor), 0, start)]
        steps: list[AlgorithmStep] = []

        while heap:
            _, distance, node = heapq.heappop(heap)
            if node in visited:
                continue
            visited.add(node)

            reached_end = node == end
            if not reached_end:
                for neighbor, weight in adjacency[node]:
                    if neighbor in visited:
                        continue

                    new_distance = distance + weight
                    if new_distance < distances[neighbor]:
                        distances[neighbor] = new_distance
                        previous[neighbor] = node
                        priority = new_distance + self._heuristic(neighbor, end, heuristic_factor)
                        heapq.heappush(heap, (priority, new_distance, neighbor))

            # Snapshot after expanding, so newly discovered frontier edges show up now.
            frontier = {n for _, _, n in heap if n not in visited}
            reached = {n: d for n, d in distances.items() if d < math.inf}
            steps.append(
                AlgorithmStep(
                    current=node,
                    visited=set(visited),
                    frontier=frontier,
                    path=[],
                    previous=dict(previous),
                    distances=reached,
                )
            )

            if reached_end:
                break

        return self._finalize_steps(steps, previous, start, end)

    def _finalize_steps(
        self,
        steps: list[AlgorithmStep],
        previous: dict[int, int],
        start: int,
        end: int,
    ) -> list[AlgorithmStep]:
        """Attaches the reconstructed path to the last step, so it only appears once \
        the algorithm has actually reached (or given up looking for) the end node."""

        path = self._reconstruct_path(previous, start, end)

        if not steps:
            return [AlgorithmStep(current=None, visited=set(), frontier=set(), path=path, previous={}, distances={})]

        steps[-1] = replace(steps[-1], path=path)
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
        current_step = self.steps[self.step_index] if 0 <= self.step_index < len(self.steps) else None
        path_edges = {
            (a, b) if a < b else (b, a)
            for a, b in zip(current_step.path, current_step.path[1:])
        } if current_step is not None else set()

        # Edges the search tree has actually traveled along, colored to match the node
        # they led to, so it's easy to see what's been explored/is frontier, not just the path.
        search_edges: dict[tuple[int, int], str] = {}
        if current_step is not None:
            for node, parent in current_step.previous.items():
                edge_key = (node, parent) if node < parent else (parent, node)
                if node in current_step.visited:
                    search_edges[edge_key] = NODE_VISITED_COLOR
                elif node in current_step.frontier:
                    search_edges[edge_key] = NODE_FRONTIER_COLOR

        for start_index, end_index in self.edges:
            start = self.nodes[start_index]
            end = self.nodes[end_index]
            edge_key = (start_index, end_index) if start_index < end_index else (end_index, start_index)

            if edge_key in path_edges:
                color, thickness = PATH_EDGE_COLOR, 4
            elif edge_key in search_edges:
                color, thickness = search_edges[edge_key], 3
            else:
                color, thickness = EDGE_COLOR, 2

            pygame.draw.line(screen, color, start, end, thickness)

            weight = math.ceil(math.dist(start, end) / EDGE_WEIGHT_FACTOR)
            label = self.weight_font.render(str(weight), True, EDGE_WEIGHT_COLOR)
            midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
            screen.blit(label, label.get_rect(center=midpoint))

        for index, position in enumerate(self.nodes):
            pygame.draw.circle(screen, self._node_color(index, current_step), position, NODE_RADIUS)
            pygame.draw.circle(screen, NODE_BORDER_COLOR, position, NODE_RADIUS, 1)

            if self.show_costs and current_step is not None and index in current_step.distances:
                cost = self._display_cost(index, current_step.distances[index])
                label = self.cost_font.render(str(round(cost, 1)), True, COST_LABEL_COLOR)
                screen.blit(label, label.get_rect(center=position))

    def _display_cost(self, index: int, cost: float) -> float:
        """A*/greedy order exploration by g + h, so their labels should reflect that, not just g."""

        if self.algorithm == "a_star":
            return cost + self._heuristic(index, self.end_node, EDGE_WEIGHT_FACTOR)
        if self.algorithm == "greedy":
            return cost + self._heuristic(index, self.end_node, 1)
        return cost

    def _node_color(self, index: int, current_step: AlgorithmStep | None) -> str:
        if current_step is not None and index in current_step.path:
            return NODE_PATH_COLOR
        if index == self.start_node:
            return NODE_START_COLOR
        if index == self.end_node:
            return NODE_END_COLOR
        if current_step is not None:
            if index in current_step.visited:
                return NODE_VISITED_COLOR
            if index in current_step.frontier:
                return NODE_FRONTIER_COLOR

        return NODE_COLOR
