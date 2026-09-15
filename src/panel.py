"""Builds the tessella widget tree used for the right-hand control panel."""

import pygame
from tessella import *

BUTTON_HEIGHT = 40
LABEL_STYLE = TextStyle(font_size=14, font_color=Palette.TEXT_SECONDARY)


class ControlPanel:
    """Owns the control panel's widget tree and the state it reacts to."""

    def __init__(self) -> None:
        self.step_duration: ValueNotifier[int] = ValueNotifier(10)
        self.node_count: ValueNotifier[int] = ValueNotifier(20)
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
        print("Generate clicked")

    def _on_step_duration_changed(self, value: int) -> None:
        self.step_duration.value = value
        print(f"Step duration: {value}")

    def _on_node_count_changed(self, value: int) -> None:
        self.node_count.value = value
        print(f"Node count: {value}")

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
