# Agent 六层架构解耦计划

> ⚠️ **本计划尚未开始执行，所有改动均为待办状态。请勿上线。**
>
> 目标：将 `MessageChatView` 中耦合的 Agent 六层（感知、记忆、规划推理、决策调度、工具调用、输出交互）逐步拆分为独立模块。

---

## 一、现状分析

当前 `MessageChatView`（`backend/web/views/friend/message/chat/chat.py`，303 行）是一个**上帝类**，同时承担了六层职责：

| 层级 | 当前代码位置 | 问题 |
|---|---|---|
| **① 感知模块** | `chat.py` 第 37~75 行 `add_system_prompt()` + `add_recent_messages()` | 直接查数据库，和 View 耦合 |
| **② 记忆模块** | `memory/graph.py` + `memory/update.py` + `chat.py` 第 256 行 | 触发逻辑嵌在 View 的保存方法里 |
| **③ 规划推理模块** | `chat/graph.py` 第 58~66 行 | 和决策调度混在一起，无法单测 |
| **④ 决策调度模块** | `chat/graph.py` 第 70~84 行 | `create_app()` 是静态方法，无法注入依赖 |
| **⑤ 工具调用模块** | `chat/graph.py` 第 25~42 行 | 和 Graph 硬编码，知识库路径写死 |
| **⑥ 输出交互模块** | `chat.py` 第 123~228 行 TTS + `event_stream()` | TTS、SSE、持久化全部塞在一起 |

---

## 二、解耦步骤（按优先级排序）

### P0 — 提取 TTS 服务（`services/tts_service.py`）

**目标**：将 `MessageChatView` 中的 TTS 相关方法提取为独立服务类。

**涉及代码**：
- `chat.py` 导入部分：删除 `base64`、`uuid4`、`websockets`、`BaseMessageChunk`、`AIMessageChunk`
- `chat.py` 第 123~228 行：删除以下 4 个方法
  - `tts_sender()`（第 123~161 行）
  - `tts_receiver()`（第 163~173 行）
  - `run_tts_tasks()`（第 176~221 行）
  - `work()`（第 223~228 行）
- `chat.py` 第 269 行：`thread = threading.Thread(target=self.work, ...)` 改为 `target=tts_service.work`

**新建文件**：`backend/web/services/tts_service.py`

```python
import asyncio
import base64
import json
import os
from queue import Queue
import threading
from uuid import uuid4
import websockets
from langchain_core.messages import BaseMessageChunk, AIMessageChunk

class TtsService:
    """TTS 语音合成服务"""

    async def tts_sender(self, app, inputs, mq: Queue, ws, task_id: str, stop_event: threading.Event):
        # 从 chat.py 第 123~161 行原样迁移
        ...

    async def tts_receiver(self, mq: Queue, ws):
        # 从 chat.py 第 163~173 行原样迁移
        ...

    async def run_tts_tasks(self, app, inputs, mq: Queue, stop_event: threading.Event):
        # 从 chat.py 第 176~221 行原样迁移
        ...

    def work(self, app, inputs, mq: Queue, stop_event: threading.Event):
        # 从 chat.py 第 223~228 行原样迁移
        ...
```

**chat.py 修改后**：
```python
# 新增导入
from web.services.tts_service import TtsService

# event_stream 方法内
# 原：thread = threading.Thread(target=self.work, args=(app, inputs, mq, stop_event))
# 改为：
tts_service = TtsService()
thread = threading.Thread(target=tts_service.work, args=(app, inputs, mq, stop_event))
```

**风险**：低，纯代码移动，无逻辑变更。

---

### P1 — 提取感知模块（`agent/perception.py`）

**目标**：将 `add_system_prompt()` 和 `add_recent_messages()` 提取为独立的 `PerceptionModule`。

**涉及代码**：
- `chat.py` 第 37~75 行：删除 `add_system_prompt()` 和 `add_recent_messages()`
- `chat.py` 第 111~112 行：
  ```python
  # 原：
  inputs = add_system_prompt(inputs, friend)
  inputs = add_recent_messages(inputs, session)
  ```

**新建文件**：`backend/web/agent/perception.py`

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

class PerceptionModule:
    """感知模块：负责把原始输入转成 LLM 消息列表"""

    def __init__(self, system_prompts: list[str], character_name: str,
                 character_profile: str, long_term_memory: str):
        self.system_prompts = system_prompts
        self.character_name = character_name
        self.character_profile = character_profile
        self.long_term_memory = long_term_memory

    def build_system_message(self) -> SystemMessage:
        prompt = "".join(self.system_prompts)
        prompt += f"\n你的名字是{self.character_name}..."
        prompt += f"【角色性格】\n{self.character_profile}\n"
        prompt += f"【长期记忆】\n{self.long_term_memory}\n"
        return SystemMessage(prompt)

    def build_context_messages(self, recent_messages: list[dict]) -> list:
        """recent_messages 由调用方查询后传入，此处不直接查数据库"""
        msgs = []
        for m in recent_messages:
            if m.get("user_message"):
                msgs.append(HumanMessage(m["user_message"]))
            msgs.append(AIMessage(m["output"]))
        return msgs

    def perceive(self, user_input: str, recent_messages: list[dict]) -> list:
        """完整的感知流程：系统提示 + 历史 + 当前输入"""
        return [
            self.build_system_message(),
            *self.build_context_messages(recent_messages),
            HumanMessage(user_input)
        ]
```

**chat.py 修改后**：
```python
from web.agent.perception import PerceptionModule

# post() 方法内：
perception = PerceptionModule(
    system_prompts=[sp.prompt for sp in SystemPrompt.objects.filter(title='回复').order_by('order_number')],
    character_name=friend.character_name or (friend.character.name if friend.character else '未知角色'),
    character_profile=friend.character_profile or (friend.character.profile if friend.character else ''),
    long_term_memory=friend.memory
)
recent = list(Message.objects.filter(session=session).order_by('-id')[:10])
recent.reverse()
messages = perception.perceive(message, recent)
inputs: AgentState = {'messages': messages}
```

**风险**：低，纯函数提取。但需注意 `add_recent_messages` 中原有的 `msgs[:1] + messages + msgs[-1:]` 拼接逻辑需保留。

---

### P2 — 提取记忆服务（`services/memory_service.py`）

**目标**：将记忆更新触发逻辑从 `MessageChatView._save_message()` 中提取。

**涉及代码**：
- `chat.py` 第 255~257 行：
  ```python
  if Message.objects.filter(session=session).count() % 10 == 0:
      update_memory(friend, session)
  ```

**新建文件**：`backend/web/services/memory_service.py`

```python
from web.views.friend.message.memory.update import update_memory

class MemoryService:
    def __init__(self, memory_module=None):
        self.memory_module = memory_module

    def update_if_needed(self, friend, session):
        """每累计 10 条消息触发一次长期记忆更新"""
        from web.models.friend import Message
        count = Message.objects.filter(session=session).count()
        if count % 10 == 0:
            update_memory(friend, session)
```

**chat.py 修改后**：
```python
from web.services.memory_service import MemoryService

# _save_message() 内删除第 255~257 行，改为：
MemoryService().update_if_needed(friend, session)
```

**风险**：低。

---

### P3 — 提取工具注册中心（`agent/tools.py`）

**目标**：将 `get_time` 和 `search_knowledge_base` 从 `ChatGraph.create_app()` 中提取。

**涉及代码**：
- `chat/graph.py` 第 25~42 行：删除内部工具定义
- `chat/graph.py` 第 44 行：`tools = [get_time, search_knowledge_base]` 改为从外部传入

**新建文件**：`backend/web/agent/tools.py`

```python
import lancedb
from langchain_core.tools import tool
from langchain_community.vectorstores import LanceDB
from web.documents.utils.custom_embeddings import CustomEmbeddings

class ToolRegistry:
    """工具注册中心，支持依赖注入"""

    def __init__(self, knowledge_base_path: str):
        self.kb_path = knowledge_base_path

    def get_tools(self):
        @tool
        def get_time() -> str:
            from django.utils.timezone import localtime, now
            return localtime(now()).strftime('%Y-%m-%d %H:%M:%S')

        @tool
        def search_knowledge_base(query: str) -> str:
            db = lancedb.connect(self.kb_path)
            embeddings = CustomEmbeddings()
            vector_db = LanceDB(connection=db, embedding=embeddings,
                              table_name='my_knowledge_base')
            docs = vector_db.similarity_search(query, k=3)
            context = '\n\n'.join([f'内容片段: {i + 1}\n{doc.page_content}' for i, doc in enumerate(docs)])
            return f'从知识库中找到以下相关信息: \n\n{context}\n'

        return [get_time, search_knowledge_base]
```

**chat/graph.py 修改后**：
```python
class ChatGraph:
    @staticmethod
    def create_app(tools=None):   # 新增 tools 参数
        if tools is None:
            from web.agent.tools import ToolRegistry
            tools = ToolRegistry('./web/documents/lancedb_storage').get_tools()
        # 后续逻辑不变
```

**风险**：中，需确保 `create_app()` 的调用方也同步修改。

---

### P4 — 重构决策调度层（`agent/orchestrator.py` + `agent/planner.py`）

**目标**：将 `ChatGraph` 从静态方法改为可实例化、可注入依赖的编排器。

**涉及代码**：
- `chat/graph.py` 第 22~85 行：整个 `ChatGraph` 类
- `chat.py` 第 107 行：`app = ChatGraph.create_app()`

**新建文件**：`backend/web/agent/planner.py`

```python
from langchain_core.messages import AIMessage

class Planner:
    """规划推理模块：LLM 的思考核心"""

    def __init__(self, llm, tools: list):
        self.llm = llm.bind_tools(tools)

    def think(self, state) -> dict:
        """LLM 推理一次，决定回复还是调用工具"""
        from typing import Sequence
        from langchain_core.messages import BaseMessage
        res = self.llm.invoke(list(state["messages"]))
        return {"messages": [res]}

    def should_continue(self, state) -> str:
        """判断是否需要进入工具调用"""
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "tools"
        return "end"
```

**新建文件**：`backend/web/agent/orchestrator.py`

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

class AgentOrchestrator:
    """决策调度模块：负责编排整个执行图"""

    def __init__(self, planner, tool_node: ToolNode, agent_state_class):
        self.planner = planner
        self.tool_node = tool_node
        self.agent_state_class = agent_state_class
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(self.agent_state_class)
        graph.add_node("agent", self.planner.think)
        graph.add_node("tools", self.tool_node)
        graph.add_edge(START, "agent")
        graph.add_conditional_edges(
            "agent",
            self.planner.should_continue,
            {"tools": "tools", "end": END}
        )
        graph.add_edge("tools", "agent")
        return graph.compile()

    async def run(self, messages: list):
        return self.graph.astream({"messages": messages}, stream_mode="messages")
```

**chat.py 修改后**：
```python
from langchain_openai import ChatOpenAI
from pydantic import SecretStr
from langgraph.prebuilt import ToolNode
from web.agent.planner import Planner
from web.agent.orchestrator import AgentOrchestrator
from web.agent.tools import ToolRegistry

# post() 方法内：
tools = ToolRegistry('./web/documents/lancedb_storage').get_tools()
planner = Planner(
    ChatOpenAI(
        model='deepseek-v3.2',
        api_key=SecretStr(os.getenv('API_KEY') or ''),
        base_url=os.getenv('API_BASE'),
        streaming=True,
        model_kwargs={"stream_options": {"include_usage": True}}
    ),
    tools
)
app = AgentOrchestrator(planner, ToolNode(tools), AgentState)
```

**风险**：高，涉及 LangGraph 核心流程，改后需完整测试对话链路。

---

### P5 — 提取业务编排层（`services/chat_service.py`）

**目标**：将 `MessageChatView` 中除 HTTP 路由外的所有逻辑抽到 `ChatService`。

**涉及代码**：
- `chat.py` 第 230~303 行：`_save_message()` + `event_stream()`
- `chat.py` 第 91~121 行：`post()` 方法

**新建文件**：`backend/web/services/chat_service.py`

```python
import json
from queue import Queue
import threading
from typing import Generator, Any

from django.utils.timezone import now

class ChatService:
    """业务编排层：组合六层模块，协调完整对话流程"""

    def __init__(self, perception, orchestrator, tts_service, memory_service):
        self.perception = perception
        self.orchestrator = orchestrator
        self.tts_service = tts_service
        self.memory_service = memory_service

    def _save_message(self, session, friend, message, inputs, full_output, full_usage):
        # 从 chat.py 第 230~257 行迁移
        ...

    def event_stream(self, app, inputs, friend, session, message) -> Generator[bytes, Any, None]:
        # 从 chat.py 第 259~303 行迁移
        # 内部调用 self.tts_service.work()
        ...
```

**chat.py 修改后**（目标：50 行以内）：
```python
class MessageChatView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [SSERenderer]

    def post(self, request):
        session_id = request.data['session_id']
        message = request.data['message'].strip()
        if not message:
            return Response({'result': '消息不能为空'})

        try:
            session = Session.objects.get(pk=session_id, friend__me__user=request.user)
        except Session.DoesNotExist:
            return Response({'result': '会话不存在'})

        friend = session.friend
        if not friend.character:
            return Response({'result': '该角色已被删除，无法继续对话'})

        # 组装 ChatService（依赖注入）
        chat_service = build_chat_service(friend)

        response = StreamingHttpResponse(
            chat_service.event_stream(...),  # 需确定参数
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response
```

**风险**：高，涉及 SSE 流式响应和线程模型，需仔细验证。

---

## 三、解耦后的目标文件结构

```
backend/web/
├── agent/                          # 新增：纯 Agent 核心
│   ├── __init__.py
│   ├── perception.py               # ① 感知模块（P1）
│   ├── planner.py                  # ③ 规划推理模块（P4）
│   ├── orchestrator.py             # ④ 决策调度模块（P4）
│   ├── tools.py                    # ⑤ 工具注册与实现（P3）
│   └── memory.py                   # ② 记忆模块接口（P2 可选）
│
├── services/                       # 新增：业务服务层
│   ├── __init__.py
│   ├── tts_service.py              # ⑥ TTS 语音合成（P0）
│   ├── memory_service.py           # ② 记忆触发逻辑（P2）
│   └── chat_service.py             # ⑥ 业务编排（P5）
│
├── views/friend/message/chat/
│   ├── chat.py                     # 目标：View 只保留 HTTP 路由（50 行以内）
│   └── graph.py                    # 目标：逐步废弃，迁移到 agent/orchestrator.py
│
└── models/ ...                     # 不变
```

---

## 四、六层调用链（目标态）

```
用户输入
    │
    ▼
┌─────────────────┐
│ ① 感知模块       │  PerceptionModule.perceive()
│ (组装 Prompt)   │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ ④ 决策调度模块   │  AgentOrchestrator.run()
│ (StateGraph)    │  ──► ┌─────────────────┐
└─────────────────┘      │ ③ 规划推理模块   │  Planner.think()
    │                    │ (LLM 思考)      │
    │                    └─────────────────┘
    │                          │
    │                    需要工具? ──是──► ┌─────────────────┐
    │                    否 ◄─────────────│ ⑤ 工具调用模块   │  ToolNode
    │                                     │ (get_time / RAG)│
    │                                     └─────────────────┘
    ▼
┌─────────────────┐
│ ⑥ 输出交互模块   │  ChatService.event_stream()
│ (SSE + TTS)     │
└─────────────────┘
    │
    ▼
┌─────────────────┐
│ ② 记忆模块       │  MemoryService.update_if_needed()
│ (保存 + 摘要)    │
└─────────────────┘
```

---

## 五、执行顺序建议

| 顺序 | 任务 | 风险 | 验证方式 |
|---|---|---|---|
| 1 | P0 — 提取 TTS 服务 | 低 | 发起带语音的对话，确认 SSE 流和音频正常 |
| 2 | P1 — 提取感知模块 | 低 | 发起普通对话，确认角色设定和历史上下文正确 |
| 3 | P2 — 提取记忆服务 | 低 | 发送 10 条消息，确认长期记忆更新触发 |
| 4 | P3 — 提取工具注册 | 中 | 测试"查时间"和"查知识库"两个工具 |
| 5 | P4 — 重构决策调度 | 高 | 完整测试多轮对话 + 工具调用链路 |
| 6 | P5 — 提取业务编排 | 高 | 端到端测试：语音对话、历史分页、会话标题生成 |

---

## 六、回滚方案

每一步改动前，建议：
1. 使用 `git stash` 或单独分支进行重构
2. 保留原始 `chat.py` 和 `graph.py` 的备份
3. 每完成一步，至少通过一次端到端对话测试后再进入下一步

---

*文档创建时间：2026-04-29*  
*状态：待执行*
