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

    human_content = [{"type": "text", "text": state["raw_prompt"]}]
    
    if state.get("logo"):
        mime_type = state["logo"]["mime_type"]
        base64_data = state["logo"]["data"]
        human_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime_type};base64,{base64_data}"}
        })

    response = agent.invoke(
        {
            "messages": [
                {"role": "system", "content": planner_agent_system_prompt},
                {"role": "human", "content": human_content},
            ]
        }
    )
    state["slide_plan"] = response["structured_response"]
    pprint("================= SLIDE PLAN ==========================")
    pprint(state["slide_plan"])
    return state
