import os
from pprint import pprint

from django.utils.timezone import localtime, now
from typing import Annotated, Sequence, TypedDict
import lancedb
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph, add_messages
from langgraph.prebuilt import ToolNode
from langchain_community.vectorstores import LanceDB
from pydantic import SecretStr

from web.documents.utils.custom_embeddings import CustomEmbeddings



class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


class ChatGraph:
    @staticmethod
    def create_app():
        @tool
        def get_time() -> str:
            """当需要查询精确时间时，调用此函数，返回格式为：[年-月-日 时:分:秒]"""
            return localtime(now()).strftime('%Y-%m-%d %H:%M:%S')
        
        @tool
        def search_knowledge_base(query: str) -> str:
            """当用户查询阿里云百炼平台的相关信息时，调用此函数，输入为要查询的问题，输出为查询结果"""
            db = lancedb.connect('./web/documents/lancedb_storage')
            embeddings = CustomEmbeddings()
            vector_db = LanceDB(
                connection=db,
                embedding=embeddings,
                table_name='my_knowledge_base',
            )
            docs = vector_db.similarity_search(query, k=3)  # 把用户的问题 query 也转成向量，然后在数据库里找最相似的 Top 3 个文档片段
            context = '\n\n'.join([f'内容片段: {i + 1}\n{doc.page_content}' for i, doc in enumerate(docs)])
            return f'从知识库中找到以下相关信息: \n\n{context}\n'

        tools = [get_time, search_knowledge_base]

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
            pprint(state['messages'])
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
