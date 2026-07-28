import operator
from typing import TypedDict, List, Optional, Annotated
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    intent: Optional[str]  # 'b2c', 'b2b', or None
    customer_age: Optional[int]
    allergies: List[str]
    safety_status: str  # 'safe', 'underage_redirect', 'hazchem_blocked'
    context: Optional[str]  # RAG context fetched from Qdrant
    tool_called: bool
