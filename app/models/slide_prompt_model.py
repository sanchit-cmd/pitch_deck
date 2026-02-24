from typing import TypedDict


class SlidePrompt(TypedDict):
    slide_type: str
    slide_number: int
    prompt: str
