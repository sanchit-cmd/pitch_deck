from pydantic import BaseModel
from enum import Enum


class StageEnum(str, Enum):
    IDEA = "Idea"
    MVP = "MVP"
    REVENUE = "Revenue"


class GoalOfDeckEnum(str, Enum):
    INVESTOR = "Investor"
    SALES = "Sales"
    COLLEGE_PROJECT = "College Project"


class ToneEnum(str, Enum):
    FORMAL = "Formal"
    CASUAL = "Casual"
    INSPIRATIONAL = "Inspirational"
    TECHNICAL = "Technical"
    STORYTELLING = "Storytelling"
    BOLD = "Bold"
    MINIMALISTIC = "Minimalistic"


class PlannerPromptSchema(BaseModel):
    company_name: str
    tagline: str
    problem: str
    solution: str
    target_customer: str
    industry: str
    business_model: str
    stage: StageEnum
    deck_goal: GoalOfDeckEnum
    competitors: str
    unique_advantage: str | None
    tone: ToneEnum
