from typing import TypedDict, List


class Slide(TypedDict):
    """Represents a single slide in the pitch deck, as planned by the planner agent and then designed by the builder agent."""

    slide_number: int
    slide_type: str
    title: str
    content_bullets: List[str]
    visual_description: str
    layout_description: str
