"""Builds the tessella widget tree used for the right-hand control panel."""

from typing import Callable

import pygame
from tessella import *

BUTTON_HEIGHT = 40
LABEL_STYLE = TextStyle(font_size=14, font_color=Palette.TEXT_SECONDARY)


class ControlPanel:
    """Owns the control panel's widget tree and the state it reacts to."""

    def __init__(self, on_generate: Callable[[int, int], None] | None = None) -> None:
        self.step_duration: ValueNotifier[int] = ValueNotifier(10)
        self.node_count: ValueNotifier[int] = ValueNotifier(20)
        self.edge_count: ValueNotifier[int] = ValueNotifier(20)
        self.on_generate = on_generate
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
        print("Start clicked")

    def _on_stop_click(self) -> None:
        print("Stop clicked")

    def _on_step_forward_click(self) -> None:
        print("+Step clicked")

    def _on_step_backward_click(self) -> None:
        print("-Step clicked")

    def _on_generate_click(self) -> None:
        print(f"Generate clicked ({self.node_count.value} nodes, {self.edge_count.value} edges)")
        if self.on_generate is not None:
            self.on_generate(self.node_count.value, self.edge_count.value)

    def _on_step_duration_changed(self, value: int) -> None:
        self.step_duration.value = value
        print(f"Step duration: {value}")

    def _on_node_count_changed(self, value: int) -> None:
        self.node_count.value = value
        print(f"Node count: {value}")

    def _on_edge_count_changed(self, value: int) -> None:
        self.edge_count.value = value
        print(f"Edge count: {value}")

    def _min_edge_count(self) -> int:
        return self.node_count.value - 1

    def _max_edge_count(self) -> int:
        # A complete graph: every node connected to every other, each edge counted once
        node_count = self.node_count.value
        return node_count * (node_count - 1) // 2

    def _build_edge_count_slider(self, _node_count: Observable) -> Widget:
        min_edges = self._min_edge_count()
        max_edges = self._max_edge_count()

        # Keeps the current edge count valid whenever node count changes the allowed range
        self.edge_count.value = max(min_edges, min(self.edge_count.value, max_edges))

        return Slider(
            key=WidgetKey(),
            min_value=min_edges,
            max_value=max_edges,
            initial_value=self.edge_count.value,
            on_changed=self._on_edge_count_changed,
        )

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
                            observable=self.node_count,
                            builder=lambda count: Text(f"Node count: {count.value}", style=LABEL_STYLE),
                        ),
                        SizedBox(height=6, width=0),
                        Slider(
                            key=WidgetKey(),
                            min_value=2,
                            max_value=64,
                            initial_value=self.node_count.value,
                            on_changed=self._on_node_count_changed,
                        ),
                        SizedBox(height=20, width=0),

                        Listener(
                            observable=self.edge_count,
                            builder=lambda count: Text(f"Edge count: {count.value}", style=LABEL_STYLE),
                        ),
                        SizedBox(height=6, width=0),
                        Listener(
                            observable=self.node_count,
                            builder=self._build_edge_count_slider,
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
                        Dropdown(
                            key=WidgetKey(),
                            items=[
                                DropdownItem("dijkstra", "Dijkstra"),
                                DropdownItem("a_star", "A*"),
                            ],
                        ),
                    ],
                ),
            ),
        )
