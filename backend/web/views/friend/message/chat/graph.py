import os
from pprint import pprint
from django.utils.timezone import localtime, now
from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph.prebuilt import ToolNode
from pydantic import SecretStr



class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


class ChatGraph:
    @staticmethod
    def create_app():
        @tool
        def get_time() -> str:
            """当需要查询精确时间时，调用此函数，返回格式为：[年-月-日 时:分:秒]"""
            return localtime(now()).strftime('%Y-%m-%d %H:%M:%S')
        
        tools = [get_time]

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
        ).bind_tools(tools)

        def modal_call(state: AgentState) -> AgentState:
            pprint(state)
            res = llm.invoke(list(state['messages']))
            return {'messages': [res]}
        
        def should_continue(state: AgentState) -> str:
            last_message = state['messages'][-1]
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                return "tools"
            return "end"
        
        tool_node = ToolNode(tools)

        graph = StateGraph(AgentState)
        graph.add_node('agent', modal_call)
        graph.add_node('tools', tool_node)

        graph.add_edge(START, 'agent')
        graph.add_conditional_edges(
            'agent',
            should_continue,
            {
                'tools': 'tools',
                'end': END
            }
        )
        graph.add_edge('tools', 'agent')

        return graph.compile()
