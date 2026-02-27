import os
from pathlib import Path
from PIL import Image

from langgraph.types import interrupt
from app.state import DeckState


def pdf_generator(state: DeckState) -> DeckState:
    """Combines generated slide images into a single PDF document."""
    
    if not state.get("slide_images"):
        return state
        
    # Get configuration block to construct a job-specific filename if running via threads
    # Fallback to default if not configured
    
    pdf_dir = Path("./pdfs/")
    pdf_dir.mkdir(exist_ok=True)
    
    # Sort images by their generated slide numbers
    valid_images = [img for img in state["slide_images"] if img and img.get("image_path")]
    valid_images.sort(key=lambda x: x["slide_number"])
    
    if not valid_images:
         raise ValueError("No valid slide images to process into PDF")

    # The file name will be an arbitrary UUID if thread id isn't passed, ideally it should be unique
    pdf_filename = "presentation.pdf" 
    pdf_path = str(pdf_dir / pdf_filename)
        
    try:
        # Open first image to initialize PDF layout
        first_img = Image.open(valid_images[0]["image_path"]).convert('RGB')
        
        # Open remaining images
        remaining_imgs = []
        for img_data in valid_images[1:]:
            remaining_imgs.append(Image.open(img_data["image_path"]).convert('RGB'))
            
        # Save all images to one PDF
        first_img.save(
            pdf_path, 
            save_all=True, 
            append_images=remaining_imgs
        )
        
        state["pdf_path"] = pdf_path
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        
    return state
