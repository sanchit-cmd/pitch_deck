from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

# Custom Imports
from prompts import agent_system_prompt as system_prompt
from tools import *
from middleware import log_tool_calls

# Load environment variables from .env file
load_dotenv()


model = init_chat_model(model=ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite"))

agent = create_deep_agent(
    model=model,
    system_prompt=system_prompt,
    tools=[search_web],
    middleware=[log_tool_calls],
)
