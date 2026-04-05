import os
from typing import Annotated, Sequence, TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph.graph.state import CompiledStateGraph 
from pydantic import SecretStr


class MemoryGraph:
    @staticmethod
    def create_app()  -> CompiledStateGraph:
        llm = ChatOpenAI(
            model='deepseek-v3.2',
            api_key=SecretStr(os.getenv('API_KEY') or ''),
            base_url=os.getenv('API_BASE'),
        )

        class AgentState(TypedDict):
            messages: Annotated[Sequence[BaseMessage], add_messages]
        
        def modal_call(state: AgentState) -> AgentState:
            res = llm.invoke(list(state['messages']))
            return {'messages': [res]}
        
        graph = StateGraph(AgentState)
        graph.add_node('agent', modal_call)

        graph.add_edge(START, 'agent')
        graph.add_edge('agent', END)

        return graph.compile()