from typing import TypedDict, Literal


class InputFormat(TypedDict):
    company_name: str
    tagline: str
    problem: str
    solution: str
    target_customer: str
    business_model: str
    stage: Literal["MVP", "IDEA", "SALES"]
    goal_of_deck: Literal["SALES", "COLLEGE_PROJECT", "INVESTOR"]
    competitors: str
    unique_advantage: str
    prefered_tone: Literal["MINIMAL", "BOLD", "CORPORATE", "FUN"]
