"""Entry point: sets up an 800x600 window split into a graph area and a
tessella-powered control panel."""

import sys

import pygame

from graph_area import GraphArea
from panel import ControlPanel

WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
GRAPH_AREA_SIZE = 1080
PANEL_WIDTH = WINDOW_WIDTH - GRAPH_AREA_SIZE

GRAPH_AREA_RECT = pygame.Rect(0, 0, GRAPH_AREA_SIZE, WINDOW_HEIGHT)
PANEL_RECT = pygame.Rect(GRAPH_AREA_SIZE, 0, PANEL_WIDTH, WINDOW_HEIGHT)

BACKGROUND_COLOR = "#1e1e1e"
GRAPH_AREA_COLOR = "#252526"
GRAPH_AREA_BORDER_COLOR = "#3c3c3c"


def draw_graph_area(screen: pygame.Surface, graph_area: GraphArea) -> None:
    """Draws the graph area's background, border and current nodes."""

    pygame.draw.rect(screen, GRAPH_AREA_COLOR, GRAPH_AREA_RECT)
    pygame.draw.rect(screen, GRAPH_AREA_BORDER_COLOR, GRAPH_AREA_RECT, 2)
    graph_area.render(screen)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Graph Algorithm Visualizer")
    clock = pygame.time.Clock()

    graph_area = GraphArea(GRAPH_AREA_RECT)
    control_panel = ControlPanel(
        on_generate=graph_area.generate,
        on_start=graph_area.start,
        on_stop=graph_area.stop,
        on_restart=graph_area.restart,
        on_step_forward=lambda: graph_area.step(1),
        on_step_backward=lambda: graph_area.step(-1),
        on_algorithm_changed=graph_area.set_algorithm,
        on_show_cost_changed=graph_area.set_show_costs,
    )
    control_panel.calculate_layout(PANEL_RECT)

    running = True
    while running:
        delta_time = clock.tick(60) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and GRAPH_AREA_RECT.collidepoint(event.pos):
                graph_area.handle_click(event.pos, event.button)
            control_panel.process_event(event)

        control_panel.update(delta_time)
        graph_area.update(control_panel.step_duration.value)

        screen.fill(BACKGROUND_COLOR)
        draw_graph_area(screen, graph_area)
        control_panel.render(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
