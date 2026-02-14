from typing import TypedDict, List, Dict, Optional


class Slide(TypedDict):
    title: str
    content: str
    notes: Optional[str]
    status: str  # success | failed


class DeckState(TypedDict):
    idea: str
    audience: str
    goal: str

    slide_outline: List[str]
    slides: Dict[str, Slide]

    regenerate_slides: List[str]  # slide titles to regenerate
    final_deck: Optional[List[Slide]]
