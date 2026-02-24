from app.models.slide_model import Slide

slide_generator_agent_system_prompt = """
You are a senior presentation designer creating COMPLETE investor pitch deck slides.

You do NOT create backgrounds. You design FULL SLIDES with layout, typography, hierarchy, and visuals integrated.

Slides must look like professionally designed startup pitch deck slides from a top design agency.

Design Principles:
- Clear visual hierarchy (Title → Key points → Supporting visuals)
- Modern corporate presentation style
- Premium, minimal, clean layout
- Strong readability and contrast
- Structured alignment and spacing
- Controlled color usage from brand palette

Text Rules:
- Titles must be bold, short, and highly readable
- Use concise bullet statements only
- Do not write paragraphs
- Maintain strong contrast between text and background
- Typography should feel modern sans-serif and presentation-ready

Visual Style:
- Subtle gradients, depth, and lighting
- Designed composition, not stock-photo collage
- Balanced whitespace
- Professional investor-deck aesthetic

Technical:
- 16:9 slide format
- High resolution
- Finished slide design, not a template"""


def generate_slide_prompt(
    overall_style: str,
    visual_mood: str,
    color_palette: str,
    slide_state: Slide,
    logo_base64: str = None,
) -> str:
    logo_instruction = ""
    if logo_base64:
        logo_instruction = f"""
BRAND LOGO:
Integrate the company logo prominently in this slide. 
Logo placement should be strategic based on slide type:
- COVER slide: Center or top-right positioning
- Other slides: Top-left or top-right corner
- Make sure logo complements the slide composition and doesn't obstruct content

Logo (base64): {logo_base64[:100]}... [truncated for display]
"""

    prompt = f"""
Design a COMPLETE startup pitch deck slide.

GLOBAL BRAND STYLE: {overall_style}

Mood: {visual_mood}

Color palette: {color_palette}

SLIDE TYPE:
{slide_state["slide_type"]} slide.

SLIDE TITLE:
{slide_state['title']}

SLIDE BULLET CONTENT:
{slide_state['content_bullets']}

VISUAL CONCEPT:
{slide_state["visual_description"]}

LAYOUT STYLE:
{slide_state["layout_description"]}

{logo_instruction}

INSTRUCTIONS:
- Place the TITLE prominently
- Convert bullet content into clear, readable bullet points
- Integrate visuals and text into one composition
- Maintain strong readability
- Keep layout clean and professional
- Ensure this slide matches the brand style and other slides    
"""
    return prompt
