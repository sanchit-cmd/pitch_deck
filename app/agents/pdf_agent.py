import os
import img2pdf
from pathlib import Path

from app.state import DeckState

def pdf_generator(state: DeckState) -> DeckState:
    """Combines generated slide images into a single PDF document losslessly."""
    
    if not state.get("slide_images"):
        return state
        
    # Use the same job_id passed in the state
    job_id = state.get("job_id", "default_job")
    
    pdf_dir = Path(f"./pdfs/{job_id}/")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    
    # Sort images by their generated slide numbers
    valid_images = [img for img in state["slide_images"] if img and img.get("image_path")]
    valid_images.sort(key=lambda x: x["slide_number"])
    
    if not valid_images:
         raise ValueError("No valid slide images to process into PDF")

    pdf_filename = "presentation.pdf" 
    pdf_path = str(pdf_dir / pdf_filename)
        
    try:
        # Get just the paths
        image_paths = [img["image_path"] for img in valid_images]
        
        # Convert losslessly to PDF using img2pdf
        with open(pdf_path, "wb") as f:
            f.write(img2pdf.convert(image_paths))
            
        state["pdf_path"] = pdf_path
        
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        
    return state
