"""Entry point: sets up an 800x600 window split into a maze area and a
tessella-powered control panel."""

import sys

import pygame

from maze_area import MazeArea
from panel import ControlPanel

WINDOW_WIDTH = 1920
WINDOW_HEIGHT = 1080
MAZE_AREA_SIZE = 1080
PANEL_WIDTH = WINDOW_WIDTH - MAZE_AREA_SIZE

MAZE_AREA_RECT = pygame.Rect(0, 0, MAZE_AREA_SIZE, WINDOW_HEIGHT)
PANEL_RECT = pygame.Rect(MAZE_AREA_SIZE, 0, PANEL_WIDTH, WINDOW_HEIGHT)

BACKGROUND_COLOR = "#1e1e1e"
MAZE_AREA_COLOR = "#252526"
MAZE_AREA_BORDER_COLOR = "#3c3c3c"


def draw_maze_area(screen: pygame.Surface, maze_area: MazeArea) -> None:
    """Draws the maze area's background, border and current maze."""

    pygame.draw.rect(screen, MAZE_AREA_COLOR, MAZE_AREA_RECT)
    pygame.draw.rect(screen, MAZE_AREA_BORDER_COLOR, MAZE_AREA_RECT, 2)
    maze_area.render(screen)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Maze Pathfinding Visualizer")
    clock = pygame.time.Clock()

    maze_area = MazeArea(MAZE_AREA_RECT)
    control_panel = ControlPanel(
        on_generate=maze_area.generate,
        on_start=maze_area.start,
        on_stop=maze_area.stop,
        on_restart=maze_area.restart,
        on_step_forward=lambda: maze_area.step(1),
        on_step_backward=lambda: maze_area.step(-1),
        on_algorithm_changed=maze_area.set_algorithm,
        on_show_cost_changed=maze_area.set_show_costs,
    )
    control_panel.calculate_layout(PANEL_RECT)

    running = True
    while running:
        delta_time = clock.tick(60) / 1000

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and MAZE_AREA_RECT.collidepoint(event.pos):
                maze_area.handle_click(event.pos, event.button)
            if event.type == pygame.MOUSEMOTION and MAZE_AREA_RECT.collidepoint(event.pos):
                left_held, _, right_held = event.buttons
                if left_held:
                    maze_area.handle_drag(event.pos, 1)
                elif right_held:
                    maze_area.handle_drag(event.pos, 3)
            control_panel.process_event(event)

        control_panel.update(delta_time)
        maze_area.update(control_panel.step_duration.value)

        screen.fill(BACKGROUND_COLOR)
        draw_maze_area(screen, maze_area)
        control_panel.render(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
