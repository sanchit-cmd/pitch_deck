# Schema for structured output
from langchain.chat_models import init_chat_model
from langchain.agents import create_agent
from dotenv import load_dotenv


class Agent:
    def __init__(self, model, model_name):
        load_dotenv()
        self.llm = init_chat_model(model=model, temperature=0.9)
        self.agent = create_agent(model=self.llm, name=model_name)

    def run(self, input):
        response = self.llm.generate(input)
        return response
