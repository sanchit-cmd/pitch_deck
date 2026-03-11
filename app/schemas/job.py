from pydantic import BaseModel
from typing import Optional, Literal

class JobRequest(BaseModel):
    user_id: Optional[str] = None
    company_name: str
    prompt: str
    num_slides: Optional[int] = 10
    prefered_tone: Literal["MINIMAL", "BOLD", "CORPORATE", "FUN"]
    logo_base64: Optional[str] = None  # Expected to be pure base64 string
    logo_mime_type: Optional[str] = "image/png"

class RegenerateRequest(BaseModel):
    new_prompt: Optional[str] = None
