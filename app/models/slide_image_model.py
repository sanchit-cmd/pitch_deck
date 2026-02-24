from typing import TypedDict


class SlideImage(TypedDict):
    """Represents the image generated for a specific slide, as output by the image generation agent."""

    slide_numer: int
    image_path: str
