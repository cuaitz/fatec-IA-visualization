"""Owns and renders the nodes and edges placed within the graph area."""

import itertools
import math
import random

import pygame

NODE_RADIUS = 12
NODE_MARGIN = NODE_RADIUS + 10
MIN_NODE_DISTANCE = NODE_RADIUS * 3
MAX_PLACEMENT_ATTEMPTS = 500

NODE_COLOR = "#686898"
NODE_BORDER_COLOR = "#eeeeee"
EDGE_COLOR = "#4a4a5a"

# How much larger the pool of nearby candidate edges is than what's actually
# needed, before randomly sampling from it. Higher values favor locality less.
LOCAL_EDGE_POOL_FACTOR = 3


class GraphArea:
    """Holds the generated nodes/edges and draws them within its bounds."""

    def __init__(self, bounds: pygame.Rect) -> None:
        self.bounds = bounds
        self.nodes: list[tuple[int, int]] = []
        self.edges: list[tuple[int, int]] = []

    def generate(self, node_count: int, edge_count: int) -> None:
        """Scatters `node_count` well-separated nodes, then connects `edge_count` pairs \
        favoring nearby nodes, for a web-like look."""

        self.nodes = self._generate_nodes(node_count)
        self.edges = self._generate_edges(edge_count)

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

    def render(self, screen: pygame.Surface) -> None:
        for start_index, end_index in self.edges:
            pygame.draw.line(screen, EDGE_COLOR, self.nodes[start_index], self.nodes[end_index], 2)

        for position in self.nodes:
            pygame.draw.circle(screen, NODE_COLOR, position, NODE_RADIUS)
            pygame.draw.circle(screen, NODE_BORDER_COLOR, position, NODE_RADIUS, 1)
