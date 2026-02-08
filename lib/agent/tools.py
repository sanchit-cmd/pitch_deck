from langchain.tools import tool


@tool
def search_web(query: str) -> str:
    """Search the web for the given query and return the results."""
    # Implement your web search logic here, e.g., using an API or web scraping
    return f"Results for '{query}'"
