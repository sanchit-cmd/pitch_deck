import os
from fastapi.templating import Jinja2Templates

# Setup React static files directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "app/templates"))
