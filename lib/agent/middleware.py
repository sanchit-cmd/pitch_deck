from langchain.tools import tool
from langchain.agents.middleware import wrap_tool_call
from deepagents import create_deep_agent

call_count = [0] 


@wrap_tool_call
def log_tool_calls(request, handler):
    """Intercept and log every tool call - demonstrates cross-cutting concern."""
    call_count[0] += 1
    tool_name = request.name if hasattr(request, "name") else str(request)

    print(f"[Middleware] Tool call #{call_count[0]}: {tool_name}")
    print(
        f"[Middleware] Arguments: {request.args if hasattr(request, 'args') else 'N/A'}"
    )

    # Execute the tool call
    result = handler(request)

    # Log the result
    print(f"[Middleware] Tool call #{call_count[0]} completed")

    return result
