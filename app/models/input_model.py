from typing import TypedDict, Literal


class InputFormat(TypedDict):
    company_name: str
    prompt: str  # Detailed brief of the company and what the presentation should cover
    prefered_tone: Literal["MINIMAL", "BOLD", "CORPORATE", "FUN"]
    num_slides: int  # Requested number of slides
