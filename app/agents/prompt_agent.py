from pprint import pprint

from app.state import DeckState
from app.prompts.generator_prompt import generate_slide_prompt


def slide_prompt(state: DeckState) -> DeckState:
    if not state.get("slide_plan"):
        raise ValueError("Slide plan is not defined in the state.")

    if not state.get("slide_prompt"):
        state["slide_prompt"] = []

    for slide in state["slide_plan"]["slides"]:
        slide_type = slide["slide_type"]
        slide_number = slide["slide_number"]

        prompt = generate_slide_prompt(
            overall_style=state["slide_plan"]["overall_style"],
            visual_mood=state["slide_plan"]["visual_mood"],
            color_palette=state["slide_plan"]["color_palette"],
            slide_state=slide,
            logo_base64=state["logo"]["data"] if state.get("logo") else None,
        )

        state["slide_prompt"].append(
            {"slide_type": slide_type, "prompt": prompt, "slide_number": slide_number}
        )

    pprint("================= SLIDE PROMPT ==========================")
    pprint(state["slide_prompt"])
    return state
