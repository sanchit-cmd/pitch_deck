from langchain.chat_models import init_chat_model

def get_llm():
    return init_chat_model(model="google_genai:gemini-2.0-pro", temperature=0.9)