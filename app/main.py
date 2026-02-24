import base64
from fastapi import FastAPI
from pprint import pprint

from app.models.input_model import InputFormat
from app.prompts.planner_prompt import generate_planner_agent_prompt
from app.state import DeckState

from app.workflow import graph

app = FastAPI()


@app.get("/")
def read_root():
    test_input: InputFormat = {
        "company_name": "HackHound PVT LTD",
        "tagline": "Crafting the Future of E-commerce",
        "problem": "Small businesses struggle to create engaging online stores that convert visitors into customers.",
        "solution": "HackHound offers an AI-powered platform that designs and optimizes e-commercestores for small businesses, increasing conversion rates and sales.",
        "target_customer": "Small business owners and entrepreneurs in the e-commerce space.",
        "industry": "E-commerce, SaaS, AI",
        "business_model": "Subscription-based with tiered pricing based on features and store size.",
        "stage": "MVP",
        "competitors": "Shopify, Wix, Squarespace",
        "unique_advantage": "AI-driven design and optimization specifically tailored for small businesses, with a focus on conversion rate improvement.",
        "prefered_tone": "BOLD",
        "goal_of_deck": "INVESTOR",
    }

    logo_data = None
    with open("file.jpg", "rb") as f:
        logo_data = f.read()
        logo_base64 = base64.b64encode(logo_data).decode("utf-8")
        logo_data = {"data": logo_base64, "mime_type": "image/jpg"}

    raw_input = generate_planner_agent_prompt(test_input, logo_base64=logo_data["data"])

    test_deck: DeckState = {
        "raw_prompt": raw_input,
    }

    if logo_data:
        test_deck["logo"] = logo_data

    config = {"configurable": {"thread_id": "1"}}
    response = graph.invoke(test_deck, config=config)

    # pprint(response)
    return {"response": response[""]}
