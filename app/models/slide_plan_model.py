from typing import TypedDict, List
from app.models.slide_model import Slide


class SlidePlan(TypedDict):
    """Plan output by the planner agent, which is then used by the builder agent to create slides and images."""

    visual_mood: str
    color_palette: str
    overall_style: str
    slides: List[Slide]
