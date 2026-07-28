from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from app.agents.state import AgentState
from app.agents.nodes import (
    router_node,
    router_edge,
    hazchem_block_node,
    b2c_mixologist_node,
    b2b_bartender_node,
    calculate_cost_tool
)

# Tool node
tool_node = ToolNode([calculate_cost_tool])

def b2b_edge(state: AgentState) -> str:
    if state.get("tool_called"):
        return "tools"
    return END

# Initialize state graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("router", router_node)
workflow.add_node("b2c_mixologist", b2c_mixologist_node)
workflow.add_node("b2b_bartender", b2b_bartender_node)
workflow.add_node("hazchem_block", hazchem_block_node)
workflow.add_node("tools", tool_node)

# Set entry point
workflow.set_entry_point("router")

# Add conditional edges from router
workflow.add_conditional_edges(
    "router",
    router_edge,
    {
        "hazchem_block_node": "hazchem_block",
        "b2b_bartender_node": "b2b_bartender",
        "b2c_mixologist_node": "b2c_mixologist"
    }
)

# Add b2b edge
workflow.add_conditional_edges("b2b_bartender", b2b_edge)

# Add edges to END
workflow.add_edge("b2c_mixologist", END)
workflow.add_edge("hazchem_block", END)
workflow.add_edge("tools", "b2b_bartender")

# Compile the graph
graph = workflow.compile()
