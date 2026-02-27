from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import InMemorySaver

from app.state import DeckState
from app.agents.planner_agent import planner_agent
from app.agents.prompt_agent import slide_prompt
from app.agents.generator_agent import image_generator_agent
from app.agents.pdf_agent import pdf_generator

checkpointer = InMemorySaver()

workflow = StateGraph(DeckState)
# Nodes
workflow.add_node("planner", planner_agent)
workflow.add_node("slide_prompt", slide_prompt)
workflow.add_node("image_generator", image_generator_agent)
workflow.add_node("pdf_generator", pdf_generator)


# Edges
workflow.add_edge(START, "planner")
workflow.add_edge("planner", "slide_prompt")
workflow.add_edge("slide_prompt", "image_generator")
workflow.add_edge("image_generator", "pdf_generator")
workflow.add_edge("pdf_generator", END)

graph = workflow.compile(checkpointer=checkpointer)
