"""Builds the tessella widget tree used for the right-hand control panel."""

from typing import Callable

import pygame
from tessella import *

BUTTON_HEIGHT = 40
LABEL_STYLE = TextStyle(font_size=14, font_color=Palette.TEXT_SECONDARY)


class _AlgorithmDropdown(Dropdown):
    """A Dropdown that also notifies a callback when the selected entry changes."""

    def __init__(
        self,
        key: WidgetKey,
        items: list[DropdownItem],
        on_changed: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(key=key, items=items)
        self.on_changed = on_changed

    def on_entry_selected(self, entry_index: int) -> None:
        super().on_entry_selected(entry_index)
        if self.on_changed is not None:
            self.on_changed(self.items[entry_index].value)


class ControlPanel:
    """Owns the control panel's widget tree and the state it reacts to."""

    def __init__(
        self,
        on_generate: Callable[[int], None] | None = None,
        on_start: Callable[[], None] | None = None,
        on_stop: Callable[[], None] | None = None,
        on_restart: Callable[[], None] | None = None,
        on_step_forward: Callable[[], None] | None = None,
        on_step_backward: Callable[[], None] | None = None,
        on_algorithm_changed: Callable[[str], None] | None = None,
    ) -> None:
        self.step_duration: ValueNotifier[int] = ValueNotifier(10)
        self.maze_size: ValueNotifier[int] = ValueNotifier(15)
        self.on_generate = on_generate
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_restart = on_restart
        self.on_step_forward = on_step_forward
        self.on_step_backward = on_step_backward
        self.on_algorithm_changed = on_algorithm_changed
        self.widget: Container = self._build()

    def calculate_layout(self, available_area: pygame.Rect) -> None:
        self.widget.calculate_layout(available_area)

    def process_event(self, event: pygame.Event) -> bool:
        return self.widget.process_event(event)

    def update(self, delta_time: float) -> None:
        self.widget.update(delta_time)

    def render(self, target_surface: pygame.Surface) -> None:
        self.widget.render(target_surface)

    def _on_start_click(self) -> None:
        if self.on_start is not None:
            self.on_start()

    def _on_stop_click(self) -> None:
        if self.on_stop is not None:
            self.on_stop()

    def _on_restart_click(self) -> None:
        if self.on_restart is not None:
            self.on_restart()

    def _on_step_forward_click(self) -> None:
        if self.on_step_forward is not None:
            self.on_step_forward()

    def _on_step_backward_click(self) -> None:
        if self.on_step_backward is not None:
            self.on_step_backward()

    def _on_algorithm_changed(self, value: str) -> None:
        if self.on_algorithm_changed is not None:
            self.on_algorithm_changed(value)

    def _on_generate_click(self) -> None:
        if self.on_generate is not None:
            self.on_generate(self.maze_size.value)

    def _on_step_duration_changed(self, value: int) -> None:
        self.step_duration.value = value

    def _on_maze_size_changed(self, value: int) -> None:
        self.maze_size.value = value

    def _build(self) -> Container:
        """Builds the widget tree for the right-hand control panel."""

        return Container(
            style=ContainerStyle(color=Palette.BACKGROUND),
            child=Padding(
                padding=EdgeInsets.all(16),
                child=Column(
                    main_axis_alignment=MainAxisAlignment.START,
                    cross_axis_alignment=CrossAxisAlignment.CENTER,
                    children=[
                        Text("Control Panel", style=TextStyle(font_size=20)),
                        SizedBox(height=20, width=0),
                        Row(
                            shrink_wrap=True,
                            cross_axis_alignment=CrossAxisAlignment.CENTER,
                            children=[
                                Button(
                                    key=WidgetKey(),
                                    text="Start",
                                    width=90,
                                    height=BUTTON_HEIGHT,
                                    on_click=self._on_start_click,
                                ),
                                SizedBox(width=8, height=0),
                                Button(
                                    key=WidgetKey(),
                                    text="Stop",
                                    width=90,
                                    height=BUTTON_HEIGHT,
                                    on_click=self._on_stop_click,
                                ),
                                SizedBox(width=8, height=0),
                                Button(
                                    key=WidgetKey(),
                                    text="Restart",
                                    width=90,
                                    height=BUTTON_HEIGHT,
                                    on_click=self._on_restart_click,
                                ),
                            ],
                        ),
                        SizedBox(height=16, width=0),
                        Listener(
                            observable=self.step_duration,
                            builder=lambda duration: Text(f"Step duration ({duration.value} frames)", style=LABEL_STYLE),
                        ),
                        SizedBox(height=6, width=0),
                        Slider(
                            key=WidgetKey(),
                            min_value=1,
                            max_value=60,
                            initial_value=self.step_duration.value,
                            on_changed=self._on_step_duration_changed,
                        ),
                        SizedBox(height=16, width=0),
                        Row(
                            shrink_wrap=True,
                            main_axis_alignment=MainAxisAlignment.CENTER,
                            children=[
                                Button(
                                    key=WidgetKey(),
                                    text="+Step",
                                    width=110,
                                    height=36,
                                    on_click=self._on_step_forward_click,
                                ),
                                SizedBox(width=12, height=0),
                                Button(
                                    key=WidgetKey(),
                                    text="-Step",
                                    width=110,
                                    height=36,
                                    on_click=self._on_step_backward_click,
                                ),
                            ],
                        ),
                        SizedBox(height=28, width=0),
                        Listener(
                            observable=self.maze_size,
                            builder=lambda size: Text(f"Maze size: {size.value}x{size.value}", style=LABEL_STYLE),
                        ),
                        SizedBox(height=6, width=0),
                        Slider(
                            key=WidgetKey(),
                            min_value=5,
                            max_value=40,
                            initial_value=self.maze_size.value,
                            on_changed=self._on_maze_size_changed,
                        ),
                        SizedBox(height=20, width=0),

                        Button(
                            key=WidgetKey(),
                            text="Generate",
                            width=160,
                            height=BUTTON_HEIGHT,
                            on_click=self._on_generate_click,
                        ),
                        SizedBox(height=28, width=0),

                        Text("Algorithm", style=LABEL_STYLE),
                        SizedBox(height=6, width=0),
                        _AlgorithmDropdown(
                            key=WidgetKey(),
                            items=[
                                DropdownItem("dijkstra", "Dijkstra"),
                                DropdownItem("a_star", "A*"),
                                DropdownItem("greedy", "Greedy A*"),
                            ],
                            on_changed=self._on_algorithm_changed,
                        ),
                    ],
                ),
            ),
        )
