from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
from pprint import pprint
from pathlib import Path
import base64
import requests
import json
import os

from app.state import DeckState
from app.models.slide_prompt_model import SlidePrompt
from app.models.logo_model import Logo

load_dotenv()


def generate_single_image(
    slide_prompt: SlidePrompt, job_id: str, logo_dict: Logo = None
) -> dict:
    slide_number = slide_prompt["slide_number"]
    prompt = slide_prompt["prompt"]
    
    # Needs to match where it was stored
    image_dir = Path(f"./slides_images/{job_id}/")
    image_dir.mkdir(parents=True, exist_ok=True)
    image_path = str(image_dir / f"slide_{slide_number}.png")

    model_id = "gemini-2.5-flash-image"
    api_key = os.getenv("GOOGLE_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"

    # Build request body
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_modalities": ["IMAGE"],
            "imageConfig": {"aspectRatio": "16:9", "imageSize": "2K"},
        },
    }

    # Add logo/reference image if provided
    if logo_dict:
        body["contents"][0]["parts"].append(
            {
                "inline_data": {
                    "data": logo_dict["data"],
                    "mime_type": logo_dict["mime_type"],
                }
            }
        )

    try:
        response = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            data=json.dumps(body),
            timeout=60,
        )

        if response.status_code != 200:
            print(
                f"Error {response.status_code} for slide {slide_number}: {response.text}"
            )
            return {"slide_number": slide_number, "image_path": None}

        response_json = response.json()
        pprint("================= IMAGE RESPONSE ==========================")
        # pprint(response)  # To avoid spamming terminal log

        # Check for empty candidates (often safety blocks)
        if not response_json.get("candidates"):
            print(f"Safety block or empty response for slide {slide_number}")
            return {"slide_number": slide_number, "image_path": None}

        # Extract the base64 data
        image_part = response_json["candidates"][0]["content"]["parts"][0]

        if "inlineData" in image_part:
            img_data_base64 = image_part["inlineData"]["data"]

            with open(image_path, "wb") as f:
                f.write(base64.b64decode(img_data_base64))

            return {"slide_number": slide_number, "image_path": image_path}

        return {"slide_number": slide_number, "image_path": None}

    except Exception as e:
        print(f"Exception for slide {slide_number}: {str(e)}")
        return {"slide_number": slide_number, "image_path": None}


def image_generator_agent(state: DeckState) -> DeckState:
    """Generate images for all slides in parallel using REST API"""
    if not state.get("slide_prompt"):
        raise ValueError("Slide prompts are not defined in the state.")

    job_id = state.get("job_id", "default_job")

    # Parallel execution for all slides
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(generate_single_image, sp, job_id, state.get("logo"))
            for sp in state["slide_prompt"]
        ]
        state["slide_images"] = [f.result() for f in futures]

    return state
