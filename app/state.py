from typing import TypedDict, Optional, List

from app.models.logo_model import Logo
from app.models.slide_image_model import SlideImage
from app.models.slide_plan_model import SlidePlan
from app.models.slide_prompt_model import SlidePrompt


class DeckState(TypedDict):
    raw_prompt: str
    logo: Optional[Logo]
    slide_plan: Optional[SlidePlan]
    slide_prompt: Optional[List[SlidePrompt]]
    slide_images: Optional[List[SlideImage]]
    pdf_path: Optional[str]
    current_slide: Optional[int]
    errors: Optional[List[str]]
    job_id: Optional[str]
