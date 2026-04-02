import os
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph, add_messages
from pydantic import SecretStr



class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


class ChatGraph:
    @staticmethod
    def create_app():
        llm = ChatOpenAI(
            model='deepseek-v3.2',
            api_key=SecretStr(os.getenv('API_KEY') or ''),
            base_url=os.getenv('API_BASE'),
            streaming=True,
            model_kwargs={
                "stream_options": {
                    "include_usage": True,
                }
            }
        )

        def modal_call(state: AgentState) -> AgentState:
            res = llm.invoke(list(state['messages']))
            return {'messages': [res]}
        
        graph = StateGraph(AgentState)
        graph.add_node('agent', modal_call)

        graph.add_edge(START, 'agent')
        graph.add_edge('agent', END)

        return graph.compile()
