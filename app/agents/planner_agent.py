from langchain.agents import create_agent
from dotenv import load_dotenv
from pprint import pprint

from app.state import DeckState
from app.models.slide_plan_model import SlidePlan
from app.prompts.planner_prompt import planner_agent_system_prompt


load_dotenv()

def planner_agent(state: DeckState) -> DeckState:
    agent = create_agent(
        model="google_genai:gemini-2.5-flash",
        response_format=SlidePlan,
    )

    response = agent.invoke(
        {
            "messages": [
                {"role": "system", "content": planner_agent_system_prompt},
                {"role": "human", "content": state["raw_prompt"]},
            ]
        }
    )
    state["slide_plan"] = response["structured_response"]
    pprint("================= SLIDE PLAN ==========================")
    pprint(state["slide_plan"])
    return state
