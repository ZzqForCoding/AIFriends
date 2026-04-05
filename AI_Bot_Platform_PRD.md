# AI Bot 平台产品需求文档 (PRD)

## 一、项目定位

一个支持 **Simple Prompt Bot** 和 **Workflow Bot** 的 AI 应用创作与分发平台。

- **C 端用户**：在 Bot 广场发现、添加并使用公开的 Bot。
- **创作者**：通过表单配置 Prompt（Simple Bot），或通过节点编排复杂 AI 工作流（Workflow Bot），并可选发布到广场供他人使用。
- **开发者**：通过平台 API Key，将公开的 Workflow Bot 集成到自己的项目中。

> 核心亮点：将 Coze 式的可视化工作流编排降维为**表单式节点配置 + 声明式 JSON DSL**，底层由 **LangGraph** 动态编译执行，兼顾可扩展性与工程可控性。

---

## 二、核心术语

| 术语 | 定义 |
|------|------|
| **Simple Bot** | 简单 Bot。仅由 System Prompt + 模型参数 +（可选）RAG 知识库组成，无复杂分支逻辑。 |
| **Workflow Bot** | 工作流 Bot。由用户通过表单/节点编辑器编排的状态图（StateGraph），底层由 LangGraph 驱动，支持条件分支、多模型串行、知识检索。 |
| **Bot 卡片** | Bot 在广场/列表中的展示单元，包含头像、名称、简介、创建者、公开状态及类型标签。 |
| **编排（Orchestration）** | 指 Workflow Bot 中节点与边的连接逻辑，决定 AI 如何根据用户输入进行多步思考与回复。 |
| **会话（Session）** | 用户与某个 Bot 的一次连续对话，包含多轮 Message。 |
| **记忆（Memory）** | Bot 能记住当前会话的上下文历史，以及可选的跨会话长期摘要。 |
| **RAG** | Retrieval-Augmented Generation，Bot 可绑定知识库，对话时先检索相关知识再生成回答。 |

---

## 三、功能需求

### 3.1 Bot 管理模块

#### 3.1.1 Bot 创建
- 用户点击「创建 Bot」，选择类型：**Simple Bot** 或 **Workflow Bot**。
- 两种 Bot 共用基础配置：
  - 名称、头像、描述
  - 选择模型（OpenAI / DeepSeek / 通义千问 / 自定义 BaseURL）
  - 填写 API Key（可选，不填则使用平台默认 Key）
  - 是否公开（默认私有）

#### 3.1.2 Bot 广场与列表
- **广场（发现页）**：展示所有用户设为「公开」的 Simple Bot 和 Workflow Bot。
- **我的 Bot**：展示用户自己创建或从广场添加的 Bot。
- **标识区分**：
  - Workflow Bot 卡片右下角带「工作流」标签。
  - Simple Bot 卡片带「智能体」标签。

#### 3.1.3 Bot 编辑与版本（MVP 简化）
- 创建者随时可以编辑自己的 Bot。
- Workflow Bot 保存即生效。MVP 阶段不实现复杂的草稿/发布版本管理，但预留该字段。

---

### 3.2 Simple Bot 配置

| 配置项 | 说明 |
|--------|------|
| **System Prompt** | 文本域，定义 Bot 的角色、技能与约束。 |
| **开场白** | Bot 首次打开时自动发送的欢迎语，可配置 3 个快捷按钮。 |
| **RAG 知识库** | 可选。支持上传 `.txt` / `.md` / `.pdf`，自动切片并向量化。 |
| **模型参数** | Temperature（MVP 阶段仅支持此项）。 |

> **实现说明**：Simple Bot 本质上是一个只有一个 `llm` 节点的 Workflow，前端用表单封装，用户无感知。

---

### 3.3 Workflow Bot 编排模块（核心亮点）

用户通过**表单式节点编辑器**编排工作流，右侧实时显示 React Flow 只读预览图。

#### 3.3.1 编排界面布局
- **左侧栏**：可点击添加的节点类型列表。
- **中间画布**：React Flow 渲染的节点关系图（只读或支持简单的节点位置拖拽）。
- **右侧抽屉**：选中节点后，弹出该节点的详细配置表单。

#### 3.3.2 支持的节点类型（MVP）

| 节点类型 | 标识 | 作用 | 必填配置 | 输出到 State |
|----------|------|------|----------|--------------|
| **开始** | `start` | 接收用户输入，作为图的起点。 | 无 | `{ user_input: string }` |
| **大模型** | `llm` | 调用大模型生成回复。 | System Prompt、是否启用 RAG | `{ ai_message: string }` |
| **条件分支** | `condition` | 根据上一步输出决定走哪条分支。 | 分支条件表达式列表 | `{ branch: string }` |
| **知识检索** | `retriever` | 从知识库检索相关文档。 | 选择知识库、Top K | `{ retrieved_docs: string }` |
| **工具调用** | `tool` | 调用外部 HTTP API。 | URL、请求方法、参数模板 | `{ tool_result: any }` |
| **结束** | `end` | 结束工作流，将指定变量作为最终答案返回。 | 选择输出变量 | 最终回复 |

#### 3.3.3 边的连接规则

1. **顺序边（Sequential Edge）**
   - 表示 A 节点执行完后直接执行 B 节点。
   - 示例：`start -> llm_1 -> end`

2. **条件边（Conditional Edge）**
   - 从一个 `condition` 节点分出多条带条件的出边。
   - 示例：
     - 条件 `"1"` -> 走到 `llm_part1`
     - 条件 `"2"` -> 走到 `llm_part2`
   - **兜底规则**：必须有一条 `default` 分支，防止所有条件不匹配时图卡死。

3. **合并边（Merge）**
   - 多个分支可以汇入同一个下游节点。
   - 示例：`llm_part1 -> end` 和 `llm_part2 -> end`。

#### 3.3.4 变量与上下文传递

- 每个节点执行后，会将其输出写入**全局 State**，键名为节点 ID。
- 下游节点可在 Prompt 或条件表达式中引用上游输出。
- **引用语法**：`{{node_id.output_key}}`
  - 示例：在 `llm_2` 的 Prompt 中写 `"请基于检索结果回答：{{retriever_1.retrieved_docs}}"`

#### 3.3.5 JSON 配置展示
- 用户编排完成后，可点击「展开 JSON」查看底层 DSL。
- 该 JSON 直接作为后端 `build_graph()` 的输入参数。

---

### 3.4 公共聊天组件

所有 Bot 共享统一的聊天界面。

#### 3.4.1 界面功能
- **消息列表**：用户消息居右，AI 消息居左，支持 Markdown、代码块高亮。
- **流式输出**：SSE 驱动打字机效果，逐字渲染。
- **快捷按钮**：开场白配置的预设按钮，点击即发送。
- **重新生成**：对最后一条 AI 消息可点击重新生成。
- **清空对话**：清空当前会话上下文。
- **语音输入**：麦克风按钮，语音识别后自动填入输入框并发送。
- **语音朗读**：每条 AI 消息旁有 🔊 按钮，TTS 朗读。

#### 3.4.2 语音输入实现
- **MVP**：浏览器原生 `Web Speech API`（`SpeechRecognition`）。
  - 优点：零成本、实时、无需后端资源。
  - 缺点：浏览器兼容性一般，但对面试项目已足够。
- **进阶（延后）**：录音上传后端，调用 Whisper API 转文字。

#### 3.4.3 语音输出实现
- **MVP**：浏览器原生 `speechSynthesis`。
- **进阶（延后）**：后端调用第三方 TTS 接口返回音频流。

---

### 3.5 RAG 知识库模块

#### 3.5.1 知识库管理
- 每个 Bot 可绑定 **0~1 个知识库**（MVP 限制）。
- 支持上传文件（`.txt`, `.md`, `.pdf`）或直接粘贴文本。
- 系统自动完成：
  1. **文本切片**（Chunking，固定长度 + 重叠）
  2. **向量化**（调用 Embedding API，如 `text-embedding-3-small`）
  3. **存储**（存入 `pgvector` 或 `ChromaDB`）

#### 3.5.2 RAG 在工作流中的使用
- **Simple Bot**：默认隐式检索，检索结果自动注入 Prompt。
- **Workflow Bot**：
  - 方式 A：在 `llm` 节点配置中勾选「启用 RAG」。
  - 方式 B：显式添加 `retriever` 节点，手动控制检索时机，并将结果注入下游 LLM。

---

### 3.6 记忆模块

#### 3.6.1 短期记忆（会话上下文）
- 每次对话将最近 **N 轮**（如 10 轮）历史消息作为 `messages` 传入 LangGraph State。
- 超过 N 轮的旧消息保留在数据库中供历史查看，但不再传入模型上下文。

#### 3.6.2 长期记忆（跨会话）
- **MVP 延后**，但数据库预留字段。
- 概念：Bot 记住用户长期偏好（如"目标雅思 7 分"）。
- 实现思路：每轮对话结束后用小模型提取关键事实写入 `LongTermMemory` 表。

---

### 3.7 开放平台 API

#### 3.7.1 API Key 管理
- 用户可在个人中心生成 `API Key`，用于调用公开 Bot。

#### 3.7.2 统一对话接口

```http
POST /api/v1/bots/{bot_id}/chat
Authorization: Bearer {user_api_key}
Content-Type: application/json

{
  "message": "你好",
  "session_id": "可选，不传则新建会话"
}
```

#### 3.7.3 返回格式

- **非流式**（默认）：
  ```json
  {
    "session_id": "xxx",
    "message": "AI 的完整回复"
  }
  ```

- **流式**（请求头带 `Accept: text/event-stream`）：
  ```text
  data: {"token": "你", "node_id": "llm_1"}

  data: {"token": "好", "node_id": "llm_1"}

  data: {"done": true, "session_id": "xxx"}
  ```

---

## 四、页面路由结构

| 路由 | 说明 |
|------|------|
| `/` | Bot 广场（发现页）。 |
| `/my-bots` | 我的 Bot 列表，入口为「创建 Bot」。 |
| `/bots/[id]/chat` | 与指定 Bot 对话的公共聊天组件。 |
| `/bots/[id]/edit` | Bot 配置页。Simple Bot 显示表单；Workflow Bot 显示编排器。 |
| `/profile` | 个人中心，含 API Key 管理。 |

---

## 五、技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Next.js 14 (App Router) + TypeScript |
| UI 样式 | Tailwind CSS + shadcn/ui |
| 状态管理 | Zustand |
| 流程画布 | @xyflow/react (React Flow) |
| 后端框架 | Django + Django REST Framework |
| AI 引擎 | LangGraph + LangChain |
| 向量数据库 | pgvector (PostgreSQL 扩展) 或 ChromaDB |
| 主数据库 | PostgreSQL |
| 部署方案 | Vercel (前端) + 云服务器 (Django) |

---

## 六、MVP 边界：重新评估（4-6 周）

> 基于 4-6 周的时间窗口和 LangGraph 学习进度，MVP 再次精简。核心原则：**只保留一个完整可讲的故事，所有非核心功能果断延后。**

### P0：必须完成（没有这些项目就不成立）

| 序号 | 功能 | 为什么必须 | 预估时间 |
|------|------|-----------|----------|
| 1 | **用户注册/登录**（JWT） | "平台"的基础身份体系 | 2 天 |
| 2 | **Simple Bot 创建/编辑/聊天** | 展示基础 AI 对话能力，也是 Workflow Bot 的兜底形态 | 3 天 |
| 3 | **Workflow Bot 表单编排器** | **核心面试亮点**。支持 `start` → `llm` → `condition` → `end` 四种节点，右侧 React Flow 只读预览图 | 7-10 天 |
| 4 | **公共聊天组件 + SSE 流式输出** | 基础用户体验，必须能看到逐字渲染 | 3 天 |
| 5 | **短期记忆（Checkpointer）** | 保证刷新页面、关闭浏览器后对话可恢复 | 2 天 |
| 6 | **Bot 广场 + 公开/私有切换** | "平台"区别于单机 Bot 的关键，支持用户共享 Bot | 3 天 |
| 7 | **部署到公网** | 面试时直接打开链接演示，说服力最强 | 2 天 |

**P0 总工期：约 4 周。**

### P1：做了加分，不做不影响面试（时间充裕时做）

| 序号 | 功能 | 实现成本 | 建议 |
|------|------|---------|------|
| 8 | **语音输入/输出** | 很低。浏览器 `Web Speech API` + `speechSynthesis`，半天到一天 | **推荐做**。零成本，演示效果惊艳 |
| 9 | **多模型选择 + 自定义 BaseURL** | 很低。前端下拉框+输入框，后端 LangChain `ChatOpenAI` 兼容国产模型 | **推荐做**。体现产品开放性 |
| 10 | **开场白 + 快捷按钮** | 很低。前端展示 3 个预设按钮，点击自动发送文本 | **推荐做**。提升产品感 |

**P1 总工期：约 3-5 天。**

### P2：明确延后（MVP 不做，面试时提一句"已预留接口"即可）

| 序号 | 功能 | 为什么不放 MVP | 面试话术 |
|------|------|---------------|----------|
| 11 | **RAG 知识库** | 太重。需要文件上传、文本切片、Embedding、向量库，一周都做不完 | "RAG 模块已预留接口，二期支持文件上传和向量检索" |
| 12 | **长期记忆** | 需要额外的 `update_memory` LLM 节点 + 数据库表 + Prompt 注入 | "已设计长期记忆提取节点，二期实现跨会话用户画像" |
| 13 | **`tool` 节点（外部 API 调用）** | 需要设计 HTTP 工具配置表单、动态编译 `@tool`、ReAct 循环调试 | "Workflow 已预留 tool 节点，二期接入搜索、天气等预设工具" |
| 14 | **MCP 协议接入** | 生态早期，调试成本高，且不是核心亮点 | "底层架构已兼容 MCP，二期可接入标准化第三方工具生态" |
| 15 | **Skill / 技能商店** | 本质上是 Tool 的 UI 包装层，MVP 阶段无增量价值 | "当前通过 Workflow 节点实现技能编排，二期考虑封装为 Skill 市场" |
| 16 | **开放 API（外部开发者调用）** | 需要 API Key 管理、鉴权、文档，对 MVP 没有增量价值 | "平台架构支持开放 API，二期对外提供标准化接口" |
| 17 | **工作流版本管理（草稿/发布）** | 增加心智负担，MVP 阶段"保存即发布"足够简单 | "当前保存即发布，二期支持草稿和版本回滚" |

### 关键修改说明

1. **RAG 明确从 MVP 移除**：RAG 是 MVP 最大的时间黑洞。面试时面试官更关心你会不会 LangGraph，而不是你会不会调 Embedding API。
2. **Tool 节点明确延后**：实现一个可用的 HTTP Tool 配置器 + 动态编译 + ReAct 循环调试，至少需要 5-7 天。MVP 阶段 Workflow 能用 `condition` 做分支判断、`llm` 做不同 Prompt 的回复，已经足够展示能力。
3. **MCP 和 Skill 明确延后**：这两个是二期加分项，MVP 阶段不要碰。
4. **语音功能反而建议做**：浏览器原生 `Web Speech API` 和 `speechSynthesis` 半天就能跑通，面试演示时"边说边聊"的效果非常惊艳，**ROI 极高**。

---

## 七、面试话术参考

> "我做了一个 **AI Bot 创作与分发平台**。前端用 **Next.js + React Flow**，后端用 **Django + LangGraph**。平台支持两种 Bot 形态：一种是面向普通用户的 **Simple Prompt Bot**，另一种是面向复杂场景的 **Workflow Bot**——用户通过表单配置节点和条件分支，底层被我设计为一套声明式 DSL，Django 端动态将其编译为 LangGraph 的 StateGraph 并流式执行。同时我实现了统一的聊天组件，支持 SSE 流式渲染、会话记忆，并预留了 RAG 与开放 API 的扩展接口。"

---

# 附录 A：项目可行性评估

## 1. 这是天马行空吗？

**不是。** 这是一个有明确市场参照、技术路径清晰的产品方向。

- **市场参照**：Coze（字节）、Dify、FastGPT、Bisheng 都是基于「Prompt Bot + Workflow + RAG」的 AI 应用平台，且都在 2023-2024 年获得了大量用户或融资。这证明需求真实存在。
- **技术可行性**：你选的 Next.js + Django + LangGraph 是业界验证过的组合，没有不可逾越的技术壁垒。
- **MVP 范围**：你把拖拽编辑器降级为表单配置 + JSON DSL，极大降低了前端工程量，使得单兵作战在 6 周内成为可能。

## 2. 市面上能跑通吗？

**作为面试作品：非常能打。**
**作为商业化产品：单兵作战很难跑通，但有明确迭代路径。**

### 为什么面试作品能打？
- 覆盖了 AI 应用工程师最核心的技能栈：LLM 调用、流式交互、状态图编排、前后端分离。
- 有完整的产品闭环（创建 -> 编排 -> 发布 -> 使用 -> 开放 API）。
- 能体现架构设计能力（DSL 设计、LangGraph 动态编译）。

### 为什么商业化很难单兵跑通？
- **成本问题**：LLM API 调用是烧钱的，如果开放给用户自定义 API Key，平台不承担成本；但如果用平台 Key，你没有资金支撑免费用户。
- **工程债务**：多租户隔离（别人的 API Key 不能泄漏）、Prompt 注入安全、文件上传安全、向量数据库运维，这些都需要时间和经验。
- **模型兼容性**：不同厂商的 API 格式（OpenAI、Claude、DeepSeek、Ollama）有细微差异，要做通用适配非常繁琐。
- **竞争问题**：Coze、Dify 已经是免费且功能强大的产品，个人项目很难在功能上超越它们。

## 3. 给你的建议

- **目标明确**：这个项目的第一目标是**拿到 AI 应用方向的 offer**，而不是创业融资。
- **聚焦亮点**：把 LangGraph 的动态编译和流式执行做深做透，前端够用即可。
- **控制范围**：严格按 MVP 清单执行，遇到可延后的功能果断砍掉。
- **部署上线**：一定要部署到公网，面试时直接打开链接演示，这比任何简历描述都有说服力。

**总结：这是一个脚踏实地、有商业原型参照、且非常适合作为求职作品的优质项目。**

---

# 附录 B：技术实现参考（供后续开发查阅）

> 以下内容记录了短期记忆、长期记忆、工具调用/MCP 扩展的实现细节与代码参考，在 MVP 完成后再逐步接入。

---

## B.1 短期记忆的实现参考

### B.1.1 为什么需要 Checkpointer

手动拼接最近 N 轮对话的方式可以应付简单 ChatBot，但在 Workflow Bot 中，一旦涉及 **断点续传、人机交互（Human-in-the-loop）、并发隔离**，就必须使用 LangGraph 原生的 `checkpointer` 作为状态持久化层。

### B.1.2 渐进式接入方案

| 阶段 | Checkpointer 类型 | 适用场景 |
|------|-------------------|----------|
| 本地开发 | `MemorySaver` | 内存存储，重启丢失，零配置 |
| MVP 上线 | `SqliteSaver` | 本地文件持久化，单实例够用 |
| 生产环境 | `PostgresSaver` | 多实例共享，支持高并发 |

### B.1.3 代码参考

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph

# 开发阶段用 MemorySaver
checkpointer = MemorySaver()

# MVP 上线后可替换为 SqliteSaver
# checkpointer = SqliteSaver.from_conn_string(":memory:")

builder = StateGraph(AgentState)
# ... 添加节点和边 ...
graph = builder.compile(checkpointer=checkpointer)

# 调用时传入 thread_id 作为会话隔离标识
config = {"configurable": {"thread_id": session_id}}
for event in graph.stream({"messages": [("user", "你好")]}, config, stream_mode="values"):
    yield event
```

### B.1.4 对话历史的注入方式

每次用户发送新消息时，前端只需传**当前这一条用户消息**。LangGraph 会自动从 `checkpointer` 中恢复该 `thread_id` 对应的历史 `state`，无需手动拼接 history。

```python
# 前端请求体
{
  "message": "今天深圳天气如何？",
  "session_id": "uuid-xxx"
}

# Django 后端
config = {"configurable": {"thread_id": request.data["session_id"]}}
for event in graph.stream({"messages": [("user", request.data["message")]}, config):
    yield f"data: {json.dumps(event)}\n\n"
```

### B.1.5 清理对话

用户点击「清空对话」时，只需删除数据库中该 `thread_id` 对应的 checkpoint 记录，或生成一个新的 `thread_id`。

---

## B.2 高级记忆管理：长期记忆与对话摘要

> 本节统一讲解两种互补的记忆技术，避免混淆：
> - **长期记忆（Long-term Memory）**：解决「跨会话记住用户是谁」，提取用户画像 JSON。
> - **对话摘要记忆（ConversationSummaryMemory）**：解决「单会话内历史太长、token 爆炸」，压缩当前会话的对话历史。
> 
> 两者不可互相替代，应根据场景组合使用。

### B.2.1 概念总览：三种记忆的分工

| 记忆类型 | 解决什么问题 | 存储位置 | 典型实现 |
|---|---|---|---|
| **短期记忆** | 会话中断后恢复、多轮上下文 | Checkpointer | `MemorySaver` / `SqliteSaver`（见 B.1） |
| **长期记忆** | 跨会话记住用户偏好、关系 | 数据库 | `update_memory` 节点 + JSON |
| **对话摘要记忆** | 单会话内历史过长、token 爆炸 | 运行时临时压缩 | `summary_buffer_node` |

**关键区别**：
- **长期记忆**关注的是**「怎么跨会话记住用户是谁」**（今天聊完，明天还记得你是雅思考生）。
- **对话摘要记忆**关注的是**「怎么在单一会话内压缩历史」**（这一句话聊了一百轮，怎么不让 token 爆掉）。

---

### B.2.2 长期记忆的实现

#### B.2.2.1 设计思路

长期记忆的核心是**跨会话记住用户画像**。实现方式是在每轮（或每 N 轮）对话结束后，将最近对话交给一个专门的「记忆提取 LLM」，输出结构化的 JSON 摘要，持久化到数据库。后续对话开始时，将该摘要注入 System Prompt。

#### B.2.2.2 LangGraph 节点设计

在 Workflow Bot 的图末尾增加一个 `update_memory` 节点，通过 `conditional_edges` 控制触发频率（如每 3 轮触发一次）。

```python
import json
from langchain_core.messages import SystemMessage, HumanMessage

def update_memory(state: AgentState):
    """记忆提取节点"""
    memory_prompt = """你是记忆管理模块。
请提取值得长期保存的信息，并更新 memory。
- 不要记录AI说话者的信息，只记录user的信息
- 不要记录闲聊
- 不要编造内容
- 合并重复信息
- 重点保留情绪与关系变化
- 总字数不要超过5000
- 只输出 JSON，不要解释

输出格式：
{
    "profile": "...",
    "relationship": "...",
    "key_events": "...",
    "recent_state": "...",
    "memory_summary": "最终给模型看的完整记忆文本（<=3000字）"
}"""

    recent_msgs = state["messages"][-6:]  # 最近 3 轮
    existing_memory = state.get("memory", {})
    
    extract_msgs = [
        SystemMessage(content=memory_prompt),
        HumanMessage(content=f"当前已有记忆：{json.dumps(existing_memory)}\n\n最新对话：{recent_msgs}")
    ]
    
    result = llm.invoke(extract_msgs)
    try:
        new_memory = json.loads(result.content)
    except json.JSONDecodeError:
        new_memory = existing_memory  # 解析失败则保持原样
    
    # 同时持久化到数据库
    LongTermMemory.objects.update_or_create(
        user_id=state["user_id"],
        bot_id=state["bot_id"],
        defaults={"memory_json": new_memory}
    )
    
    return {"memory": new_memory}


def should_update_memory(state: AgentState):
    """控制记忆更新频率"""
    human_msg_count = len([m for m in state["messages"] if isinstance(m, HumanMessage)])
    if human_msg_count % 3 == 0:
        return "update_memory"
    return "end"

# 在图构建时
builder.add_node("update_memory", update_memory)
builder.add_conditional_edges("agent", should_update_memory, {
    "update_memory": "update_memory",
    "end": END
})
builder.add_edge("update_memory", END)
```

#### B.2.2.3 Django 数据模型

```python
from django.db import models

class LongTermMemory(models.Model):
    user_id = models.IntegerField()
    bot_id = models.IntegerField()
    memory_json = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ("user_id", "bot_id")
```

#### B.2.2.4 记忆注入 Prompt

在 `agent` 节点（或任何 `llm` 节点）中，从数据库读取记忆并注入 System Prompt：

```python
def agent(state: AgentState):
    # 从数据库读取长期记忆
    mem_record = LongTermMemory.objects.filter(
        user_id=state["user_id"], 
        bot_id=state["bot_id"]
    ).first()
    
    memory_text = mem_record.memory_json.get("memory_summary", "") if mem_record else ""
    
    system_prompt = f"你是用户的助手。\n\n[用户记忆]\n{memory_text}\n\n请基于以上记忆和当前对话进行回复。"
    
    msgs = [SystemMessage(content=system_prompt)] + state["messages"]
    response = llm.invoke(msgs)
    return {"messages": [response]}
```

---

### B.2.3 对话摘要记忆（ConversationSummaryMemory）的实现

#### B.2.3.1 核心概念

当对话轮数过多时，如果把全部历史消息都塞进 Prompt，会导致 **token 爆炸**（超出模型上下文窗口，且 API 费用剧增）。`ConversationSummaryMemory` 的核心思想是：**用 LLM 把早期对话总结成一段精简摘要，只保留最近几轮原文**。

#### B.2.3.2 方案 1：SummaryBuffer（最推荐）

**策略**：保留最近 `k` 轮原始对话，把更早的对话总结成一段摘要，两者一起传给 LLM。

```python
from typing import List
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage

def summary_buffer_node(state: AgentState, max_recent_turns: int = 4):
    """
    混合摘要记忆节点：保留最近 N 轮原文，更早的总结为摘要。
    注意：max_recent_turns 是指用户+AI 的回合对数，即 message 数量为 2*N。
    """
    messages: List[BaseMessage] = state["messages"]
    
    # 如果消息不多，无需摘要
    if len(messages) <= max_recent_turns * 2:
        return {"messages": messages}
    
    # 保留最近 N 轮原文
    recent_messages = messages[-max_recent_turns * 2:]
    
    # 更早的消息用于生成摘要
    old_messages = messages[:-max_recent_turns * 2]
    
    summary_prompt = f"""请将以下对话历史总结为一段精炼的摘要，保留关键事实和上下文，不超过 200 字：

{old_messages}
"""
    summary = llm.invoke([HumanMessage(content=summary_prompt)]).content
    
    # 组装新的消息列表：[摘要系统消息] + [最近 N 轮原文]
    new_messages = [
        SystemMessage(content=f"【历史摘要】{summary}")
    ] + recent_messages
    
    return {"messages": new_messages}
```

**在图中的位置**：

```python
builder.add_node("summary_buffer", summary_buffer_node)

# 每次用户发新消息前，先执行摘要压缩
builder.add_edge("start", "summary_buffer")
builder.add_edge("summary_buffer", "agent")
```

#### B.2.3.3 方案 2：Rolling Summary（全摘要）

**策略**：不保留任何早期原文，把全部历史对话逐步总结为一段不断更新的摘要。适合 50+ 轮的超长对话。

```python
def rolling_summary_node(state: AgentState):
    messages = state["messages"]
    existing_summary = state.get("conversation_summary", "")
    
    # 只取最近 2 条（1 轮）来更新摘要
    latest_turn = messages[-2:] if len(messages) >= 2 else messages
    
    prompt = f"""你正在维护一段对话的滚动摘要。请根据已有的摘要和最新一轮对话，生成一段新的摘要（不超过 300 字）。

【已有摘要】
{existing_summary}

【最新对话】
{latest_turn}

【新摘要】
"""
    new_summary = llm.invoke([HumanMessage(content=prompt)]).content
    
    # 用摘要替换掉除最近一轮外的所有历史消息
    new_messages = [
        SystemMessage(content=f"【对话摘要】{new_summary}")
    ] + latest_turn
    
    return {
        "messages": new_messages,
        "conversation_summary": new_summary
    }
```

#### B.2.3.4 方案 3：LangChain 原生类（快速验证）

如果你只是想快速验证效果，可以直接用 LangChain 原生的 `ConversationSummaryBufferMemory`，但要注意：**它主要是为旧版 `Chain` 设计的，与 LangGraph 的 `StateGraph` 配合需要手动转换**。

```python
from langchain.memory import ConversationSummaryBufferMemory

memory = ConversationSummaryBufferMemory(
    llm=llm,
    max_token_limit=1000,
    return_messages=True
)

# 手动加载历史
for msg in state["messages"]:
    if isinstance(msg, HumanMessage):
        memory.chat_memory.add_user_message(msg.content)
    elif isinstance(msg, AIMessage):
        memory.chat_memory.add_ai_message(msg.content)

# 获取压缩后的消息列表
compressed_messages = memory.load_memory_variables({})["history"]
```

**不推荐在 LangGraph 生产代码中直接使用**，因为它与 `StateGraph` 的 `state` 管理理念有冲突，且每次都要手动 `add_message`，性能开销大。

---

### B.2.4 如何选择与组合

| 场景 | 推荐方案 | 原因 |
|---|---|---|
| **跨会话记住用户** | 长期记忆（B.2.2） | 提取用户画像 JSON，持久化到数据库 |
| **日常多轮对话（10~30 轮）** | SummaryBuffer（B.2.3.2） | 兼顾准确性和 token 控制 |
| **超长对话（50+ 轮）** | Rolling Summary（B.2.3.3） | Token 最稳定，适合客服 |
| **快速原型验证** | LangChain 原生类（B.2.3.4） | 零开发成本，但不可扩展 |

**组合建议**：
1. **Checkpointer**（B.1）负责**原始完整对话**的持久化与断点续传。
2. **SummaryBuffer**（B.2.3）负责在**运行时临时压缩**过长的 messages 后传给 LLM。
3. **长期记忆**（B.2.2）负责在**跨会话**时把用户画像注入 System Prompt。

```python
# 三者结合示例
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

builder.add_node("summary_buffer", summary_buffer_node)
builder.add_node("agent", agent)  # agent 内部已注入长期记忆
builder.add_node("update_memory", update_memory)

builder.add_edge("start", "summary_buffer")
builder.add_edge("summary_buffer", "agent")
builder.add_conditional_edges("agent", should_update_memory, {
    "update_memory": "update_memory",
    "end": END
})
builder.add_edge("update_memory", END)

graph = builder.compile(checkpointer=checkpointer)
```

### B.2.5 前端用户体验

- **长期记忆触发**：用户无感知，但每次打开 Bot 时，Bot 会自然地称呼你的名字或提到之前的偏好。
- **摘要压缩触发**：在聊天界面顶部显示一行弱提示：「前面的消息已自动摘要」，用户点击后可展开查看原始完整历史（从 checkpoint 中读取）。

### B.2.6 面试话术

> "我的 Bot 平台实现了三层记忆体系：底层用 **LangGraph Checkpointer** 做短期记忆的持久化与断点续传；中层用 **ConversationSummaryBufferMemory** 对单会话内的超长历史做动态摘要压缩，平衡 token 成本与上下文连贯性；顶层用独立的 **update_memory 节点**提取跨会话的长期用户画像（JSON 格式），注入后续对话的 System Prompt 中。"

---

## B.3 工具调用与 MCP 扩展

### B.3.1 工具调用在 Workflow Bot 中的位置

工具调用（Function Call）是 LLM 在推理过程中发出的「我需要调用外部能力」的信号。在 Workflow Bot 中，这对应于 `tool` 节点。其执行流程为：

```
llm 节点（模型输出 tool_calls）
    ↓
condition 节点（判断是否存在 tool_calls）
    ↓
tool 节点（执行具体工具逻辑）
    ↓
（可选）tool 结果回传给 llm 节点继续推理（ReAct 循环）
    ↓
end 节点
```

### B.3.2 内置 Tool：用户自定义 HTTP API

MVP 阶段，`tool` 节点的配置表单设计如下：

| 配置项 | 说明 | 示例 |
|--------|------|------|
| 工具名称 | 用于 Function Call 识别 | `search_web` |
| 工具描述 | 让 LLM 知道何时调用该工具 | "当需要获取实时信息时使用" |
| 请求 URL | HTTP 接口地址 | `https://api.tavily.com/search` |
| 请求方法 | GET / POST / PUT | `POST` |
| Headers | JSON 格式请求头 | `{"Authorization": "Bearer xxx"}` |
| 参数模板 | 支持引用上下文变量 | `{"query": "{{start.user_input}}"}` |
| 超时时间 | 秒 | `30` |

**后端动态编译示例：**

```python
import requests
from langchain.tools import tool
from string import Template

def build_http_tool(node_config: dict):
    """根据用户配置的 HTTP API 动态生成 LangChain Tool"""
    
    @tool(name=node_config["name"], description=node_config["description"])
    def http_tool(**kwargs):
        # 渲染参数模板（将 {{variable}} 替换为实际值）
        body_template = Template(json.dumps(node_config["body"]))
        rendered_body = body_template.safe_substitute(kwargs)
        
        response = requests.request(
            method=node_config["method"],
            url=node_config["url"],
            headers=node_config.get("headers", {}),
            data=rendered_body,
            timeout=node_config.get("timeout", 30)
        )
        return response.text
    
    return http_tool
```

### B.3.3 内置 Tool：平台预设工具

平台可以提供几个常用的预设 Tool，用户在 `tool` 节点配置中直接选择：

| 预设工具 | 实现方式 | 说明 |
|----------|----------|------|
| `web_search` | Tavily API / Bing API | 联网搜索 |
| `web_reader` | Jina AI Reader API | 读取指定 URL 的网页内容 |
| `weather_query` | 和风天气 / OpenWeatherMap | 查询城市天气 |
| `calculator` | Python `eval`（安全沙箱） | 数学计算 |

```python
@tool
def web_search(query: str) -> str:
    """当需要获取实时互联网信息时使用此工具。"""
    response = requests.post(
        "https://api.tavily.com/search",
        json={"query": query, "max_results": 3, "api_key": settings.TAVILY_API_KEY}
    )
    return json.dumps(response.json()["results"])
```

### B.3.4 工具节点与 LangGraph 的绑定

在 `build_graph()` 函数中，将所有 `tool` 节点统一注册到 Agent 或图中：

```python
from langgraph.prebuilt import ToolNode

def build_graph(config_json):
    builder = StateGraph(AgentState)
    
    # 1. 收集所有 tool 节点配置
    tool_configs = [n for n in config_json["nodes"] if n["type"] == "tool"]
    tools = []
    
    for tc in tool_configs:
        if tc.get("preset"):
            tools.append(PRESET_TOOLS[tc["preset"]])
        else:
            tools.append(build_http_tool(tc))
    
    # 2. 使用 ToolNode 批量执行工具
    tool_node = ToolNode(tools)
    builder.add_node("tools", tool_node)
    
    # 3. 条件分支：llm 节点输出 tool_calls 时走到 tools
    builder.add_conditional_edges("agent", should_continue, {
        "tools": "tools",
        "end": END
    })
    
    # 4. 工具执行完回到 agent 继续推理（ReAct 循环）
    builder.add_edge("tools", "agent")
    
    return builder.compile()
```

### B.3.5 MCP 扩展路径

MCP（Model Context Protocol）不是 Tool 本身，而是**外部 Tool 生态的标准化接入协议**。未来引入 MCP 后，平台可以无缝对接第三方 MCP Server（如 GitHub、Slack、文件系统、数据库等），而无需为每个服务写独立的对接代码。

**扩展时机**：MVP 完成后，作为二期功能实现。

**技术接入方案：**

```python
# 伪代码：通过 langchain-mcp-adapters 加载 MCP Server 中的 tools
from langchain_mcp_adapters.tools import load_mcp_tools

async def load_mcp_tools_for_bot(mcp_configs: list):
    """
    mcp_configs 示例：
    [
      {"name": "github", "transport": "sse", "url": "http://localhost:3001/sse"},
      {"name": "slack", "transport": "stdio", "command": "npx", "args": ["-y", "@slack/mcp-server"]}
    ]
    """
    all_tools = []
    for cfg in mcp_configs:
        tools = await load_mcp_tools(cfg)
        all_tools.extend(tools)
    return all_tools
```

**前端配置设计：**
- 在 Bot 配置页新增「MCP 连接」Tab。
- 用户填写 MCP Server 的地址和传输方式（SSE / STDIO）。
- 后端连接成功后，自动将该 Server 暴露的所有 Tools 加载到当前 Bot 的工具列表中。

**面试话术储备：**
> "目前我的平台支持用户自定义 HTTP Tool 和平台预设 Tool，底层通过 LangGraph 的 `ToolNode` 实现 ReAct 循环。二期规划引入 **MCP 协议**作为工具接入层，让用户能够即插即用地使用第三方 MCP Server（如 GitHub、Slack、本地文件系统），从而扩展 Bot 的能力边界。"

---

## B.4 Context Engine 上下文引擎设计

> Context Engine 不是某个特定的官方库，而是 AI 应用架构中的**核心模块**——它负责在调用 LLM 之前，把 System Prompt、长期记忆、RAG 检索结果、工具结果、对话历史等所有信息源，组装成最终传递给大模型的上下文（Context）。

### B.4.1 为什么需要 Context Engine？

大模型本身是无状态的，它每次只能看到**当前这一坨 Prompt**。在 Bot 平台中，Prompt 的构成可能非常复杂：

| 信息来源 | 来源模块 | 作用 |
|---------|---------|------|
| **系统指令** | Bot 配置（System Prompt） | 定义角色、技能、约束 |
| **短期记忆** | Checkpointer / 历史消息 | 提供当前会话的多轮上下文 |
| **长期记忆** | `update_memory` 节点 | 注入跨会话的用户画像 |
| **RAG 检索结果** | `retriever` 节点 / 向量库 | 提供外部知识库参考 |
| **工具结果** | `tool` 节点 | 提供计算器、搜索等实时数据 |
| **环境变量** | Bot 配置中的变量 | 替换 `{{current_date}}` 等占位符 |
| **用户当前输入** | `start` 节点 | 当前用户的最新问题 |

如果没有一个统一的组装层，`agent` 节点会变成一个巨大的"拼字符串"函数，既难维护也难调试。

### B.4.2 Context Engine 与 RAG / Memory 的关系

这三者非常容易混淆，核心区别在于**分工不同**：

| 概念 | 本质 | 和 Context Engine 的关系 |
|------|------|-------------------------|
| **RAG** | 从外部知识库**检索**信息的技术 | RAG 是 Context Engine 的**信息来源之一** |
| **Memory** | 存储和提取**历史交互**的技术 | Memory 也是 Context Engine 的**信息来源之一** |
| **Context Engine** | **组装 Prompt 的引擎/逻辑层** | 它调用 RAG、调用 Memory，然后把所有结果拼成完整上下文 |

**形象比喻**：
- RAG 是**图书管理员**（帮你找书）
- Memory 是**个人助理**（记得你的喜好）
- Context Engine 是**秘书**（在开会前把资料、备忘录、偏好整理成一份简报递给老板/LLM）

### B.4.3 在 LangGraph 中的实现

LangGraph 中没有官方的 `ContextEngine` 类，但在工程实践中可以自然封装出一个。以下是一个适合本项目的实现示例：

```python
from typing import List
from langchain_core.messages import SystemMessage

class ContextEngine:
    def __init__(self, bot_config, long_term_memory=None):
        self.system_prompt = bot_config.get("system_prompt", "")
        self.memory = long_term_memory or {}
    
    def build_messages(self, state: AgentState) -> List:
        """组装最终传给 LLM 的完整消息列表"""
        parts = [self.system_prompt]
        
        # 1. 注入长期记忆
        if self.memory.get("memory_summary"):
            parts.append(f"\n[用户记忆]\n{self.memory['memory_summary']}")
        
        # 2. 注入 RAG 检索结果（如果 state 中有）
        if state.get("retrieved_docs"):
            parts.append(f"\n[参考资料]\n{state['retrieved_docs']}")
        
        # 3. 注入工具结果（如果 state 中有）
        if state.get("tool_result"):
            parts.append(f"\n[工具结果]\n{state['tool_result']}")
        
        # 4. 组装 SystemMessage
        system_msg = SystemMessage(content="\n".join(parts))
        
        # 5. 拼接历史对话 + 当前用户输入
        # messages 已经由 checkpointer 或上游节点维护好
        return [system_msg] + list(state.get("messages", []))

# 在 agent 节点中使用
context_engine = ContextEngine(bot_config=bot_config, long_term_memory=memory)

def agent(state: AgentState):
    messages = context_engine.build_messages(state)
    response = llm.invoke(messages)
    return {"messages": [response]}
```

### B.4.4 信息拼接顺序的最佳实践

根据大模型 Attention 的特性（对 Prompt 末尾内容更敏感），推荐按以下顺序排列：

```
1. System Prompt（角色定义）
2. 长期记忆（用户画像，相对静态）
3. RAG 检索结果 / 工具结果（参考信息）
4. 会话摘要（早期对话的压缩）
5. 最近 N 轮原始对话（动态，但较旧）
6. 用户当前输入（放在最末尾，模型最关注）
```

### B.4.5 面试话术

> "在我的 Bot 平台架构中，我抽象了一个 **Context Engine** 模块，它负责在每次调用 LLM 之前，将 System Prompt、长期记忆、RAG 检索结果、对话历史等上下文源整合成最终的消息列表。这样设计的好处是**解耦了信息检索和 Prompt 组装**——RAG 模块只关心怎么召回最相关的文档，Memory 模块只关心怎么提取用户画像，而 Context Engine 则像一个调度中枢，决定这些信息的拼接顺序、权重和格式化方式。"

---

**以上四部分为后续功能扩展的详细实现备忘，MVP 阶段优先保证：Checkpointer 短期记忆 + 基础 HTTP Tool 节点。**



---

# 附录 C：LangGraph 核心概念与状态设计（知识补充）

> 本节记录 LangGraph 中容易混淆但面试高频考察的核心概念，包括 Graph 类型选择、`Annotated` 与 `reducer` 机制、以及 `AgentState` 的字段设计。所有概念均映射到 Bot 平台的具体应用场景。

---

## C.1 StateGraph vs MessageGraph：该用哪个？

LangGraph 目前提供两种 Graph 类型，核心区别在于**状态的自由度**。

| 维度 | `StateGraph` | `MessageGraph` |
|------|--------------|----------------|
| **状态定义** | 自定义 `TypedDict`，可包含任意字段 | 固定为 `List[BaseMessage]`，无需自定义 |
| **灵活性** | 高。可存储计数器、用户信息、中间产物、分支结果等 | 低。只能存消息列表 |
| **适用场景** | **复杂 Workflow、ReAct Agent、多条件分支** | 极简 ChatBot，只做消息来回 |
| **在本项目中的使用** | **必选**。Workflow Bot 需要存储 `user_id`、`memory`、`branch` 等非消息字段 | 不适用。Simple Bot 虽然简单，但为了架构统一也基于 `StateGraph` 实现 |

### 代码对比

**StateGraph（本项目使用）：**
```python
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    current_branch: str

builder = StateGraph(AgentState)
```

**MessageGraph（极简聊天）：**
```python
from langgraph.graph import MessageGraph
builder = MessageGraph()
# 状态默认就是消息列表，无法扩展其他字段
```

### 本项目场景映射
- **Workflow Bot 的表单编排器**必须使用 `StateGraph`，因为节点之间需要传递 `condition` 分支结果、`llm` 节点的中间输出、甚至未来的 `tool_result`。
- **Simple Bot** 虽然只有一个 `llm` 节点，但为了与 Workflow Bot 共用同一套执行引擎，也统一使用 `StateGraph`（此时状态里只有 `messages` 一个字段）。

---

## C.2 `Annotated[T, reducer]`：LangGraph 的状态更新机制

### 核心问题

LangGraph 的图可能有多个节点，甚至并行执行。当两个节点**同时修改同一个 State 字段**时，LangGraph 必须知道：**是覆盖？追加？还是累加？**

`Annotated[T, reducer]` 就是用来声明这个**合并策略**的。

### 语法拆解

```python
messages: Annotated[Sequence[BaseMessage], add_messages]
#        ↑ 字段类型是 BaseMessage 序列    ↑ 更新时用 add_messages 策略合并
```

### 内置 reducer：`add_messages`

```python
from langgraph.graph.message import add_messages

current = [HumanMessage("你好")]
new = [AIMessage("有什么可以帮你？")]

result = add_messages(current, new)
# 结果：[HumanMessage("你好"), AIMessage("有什么可以帮你？")]
```

**行为**：新消息追加到旧消息列表末尾，而不是覆盖。

### 如果没有 reducer 会怎样？

```python
class BadState(TypedDict):
    messages: list  # 没有 Annotated + reducer
```

如果 `node_A` 返回 `messages=[msg_A]`，`node_B` 返回 `messages=[msg_B]`，LangGraph 会**用后者直接覆盖前者**，导致 `msg_A` 丢失。

### 本项目场景映射

| State 字段 | reducer | 场景说明 |
|------------|---------|---------|
| `messages` | `add_messages` | **必须**。Bot 平台中每次对话都是追加新消息，不能覆盖历史。无论是用户输入、AI 回复、还是未来的 Tool 结果，都要追加到消息列表中。 |
| `counter` | 无 / 自定义 `add_ints` | 可选。记录对话轮数，用于触发长期记忆更新（如每 3 轮更新一次）。 |
| `memory` | 无 / 自定义 `merge_dicts` | 长期记忆的 JSON 数据。`update_memory` 节点返回新的 `memory`，需要与旧的合并而不是全量覆盖。 |

---

## C.3 AgentState 字段设计与场景映射

`AgentState` 是 `StateGraph` 的全局状态容器。Bot 平台中，以下字段是常见且合理的设计：

### C.3.1 完整字段示例

```python
from typing import TypedDict, Annotated, Sequence, Any
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    # ===== 核心对话字段 =====
    # 对话历史。必须使用 add_messages，保证多节点并行时消息追加不丢失。
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # ===== 用户与 Bot 标识字段 =====
    # 当前用户 ID，用于从数据库读取长期记忆、隔离会话。
    user_id: str
    # 当前 Bot ID，用于加载 Bot 配置（Prompt、模型参数等）。
    bot_id: int
    
    # ===== 计数与追踪字段 =====
    # 当前会话的对话轮数（HumanMessage 数量）。
    # 用于控制长期记忆更新频率（如每 3 轮触发一次 update_memory）。
    turn_count: int
    
    # ===== 长期记忆字段 =====
    # 跨会话的用户画像 JSON。update_memory 节点提取后写入，agent 节点读取注入 Prompt。
    memory: dict
    
    # ===== 摘要记忆字段 =====
    # 单会话内的滚动摘要。summary_buffer_node 生成，用于压缩超长历史。
    conversation_summary: str
    
    # ===== 工作流中间产物 =====
    # 条件分支节点的输出，记录当前走了哪个分支（如 "part1" / "part2"）。
    # 用于调试、追踪、前端高亮当前执行路径。
    last_branch: str
    
    # ===== 未来扩展字段 =====
    # Tool 节点的执行结果（二期接入 tool 节点时使用）。
    tool_result: Any
    # RAG 检索到的文档内容（二期接入 RAG 时使用）。
    retrieved_docs: str
```

### C.3.2 字段场景映射表

| 字段 | 在 Bot 平台中的作用 | 哪个节点会读写它 |
|------|-------------------|----------------|
| `messages` | 存储完整的用户/AI/Tool 对话历史，是 LLM 调用的核心上下文。 | 所有节点都会读写。`start` 追加用户输入，`llm` 追加 AI 回复，`tool` 追加工具结果。 |
| `user_id` / `bot_id` | 会话隔离与配置加载。`user_id` 用于读取长期记忆，`bot_id` 用于加载 System Prompt 和模型参数。 | `agent` 节点读取，注入 Prompt 和查数据库。 |
| `turn_count` | 控制长期记忆的触发频率。例如每 3 轮 HumanMessage 触发一次 `update_memory`。 | `should_update_memory` 条件节点读取判断。 |
| `memory` | 跨会话的用户画像（如"雅思考生，目标7分"）。让 Bot 具备"认识用户"的能力。 | `update_memory` 节点写入，`agent` 节点读取注入 System Prompt。 |
| `conversation_summary` | 单会话内的历史摘要。当对话超过 20 轮时，用摘要替代早期原文，节省 token。 | `summary_buffer_node` 生成并写入，`agent` 节点读取注入 Prompt。 |
| `last_branch` | 记录 Workflow 当前走了哪个分支。前端可用它来高亮执行路径。 | `condition` 节点写入，前端调试面板读取展示。 |
| `tool_result` | 工具调用的返回值。ReAct 循环中，LLM 基于 tool_result 继续推理。 | `tool` 节点写入，`agent` 节点读取。 |
| `retrieved_docs` | RAG 检索结果。注入到 LLM Prompt 中作为参考知识。 | `retriever` 节点写入，`llm` 节点读取。 |

---

## C.4 自定义 reducer 示例

当内置的 `add_messages` 不够用时，可以自己写 reducer。

### 示例 1：整数累加（用于 turn_count）

```python
def add_ints(a: int, b: int) -> int:
    return a + b

class AgentState(TypedDict):
    turn_count: Annotated[int, add_ints]
    # 如果 node_A 返回 turn_count=1，node_B 返回 turn_count=1
    # 最终 state 中的 turn_count = 2
```

**场景**：每个 `llm` 节点执行后都返回 `turn_count=1`，用于累计对话轮数。

### 示例 2：字典合并（用于 memory）

```python
def merge_dicts(a: dict, b: dict) -> dict:
    result = a.copy()
    result.update(b)
    return result

class AgentState(TypedDict):
    memory: Annotated[dict, merge_dicts]
    # 旧 memory {"profile": "小明"}
    # 新 memory {"relationship": "朋友"}
    # 最终 {"profile": "小明", "relationship": "朋友"}
```

**场景**：`update_memory` 节点可能只更新了 `memory` 中的某几个 key，不想覆盖已有的 `profile` 或 `key_events`。

### 示例 3：列表去重追加（用于 tags）

```python
def merge_unique_lists(a: list, b: list) -> list:
    return list(dict.fromkeys(a + b))

class AgentState(TypedDict):
    tags: Annotated[list, merge_unique_lists]
```

**场景**：多个节点都给用户打标签（如"急躁"、"理性"），合并时自动去重。

---

## C.5 常见误区

### 误区 1：所有字段都必须加 reducer
**不是。** 只有可能被**多个节点同时修改**的字段才需要 reducer。像 `user_id`、`bot_id` 这种只读字段，直接写 `str` / `int` 即可。

### 误区 2：`add_messages` 只能用于 messages
**不是。** 任何列表类型的字段都可以用 `add_messages` 作为 reducer，只要语义上是"追加"即可。但通常建议只给 `messages` 用，避免混淆。

### 误区 3：`MessageGraph` 可以做复杂 Workflow
**不能。** `MessageGraph` 的状态固定为消息列表，无法存储 `last_branch`、`tool_result` 等中间状态。复杂 Workflow 必须用 `StateGraph`。

---

## C.6 面试话术

> "在设计 Workflow Bot 的执行引擎时，我选择了 LangGraph 的 `StateGraph` 而非 `MessageGraph`，因为前者支持自定义状态字段，能够存储节点中间产物、分支结果和用户信息。其中 `messages` 字段使用了 `Annotated[Sequence[BaseMessage], add_messages]`，这是 LangGraph 的状态更新策略声明，确保多节点并行时新消息会被追加而不是覆盖。此外，我还设计了 `memory`、`conversation_summary`、`last_branch` 等字段，分别支撑长期记忆、摘要压缩和流程追踪能力。"

---

**总结：理解 `StateGraph` + `Annotated` + `reducer` 这三者，是掌握 LangGraph 状态管理的关键，也是面试中区分"会用"和"理解原理"的分水岭。**


---

# 附录 D：RAG 原理与向量数据库选型（知识补充）

> 本节记录 RAG（检索增强生成）的完整技术原理，以及向量数据库选型的对比分析。

---

## D.1 RAG 的核心流程

RAG 的本质是：**让大模型在回答问题之前，先从知识库中检索到相关的参考文本，再把检索结果和用户问题一起放进 Prompt，让模型基于这些"参考资料"生成回答。**

完整流程如下：

```
用户上传一本《雅思口语宝典》PDF
        ↓
1. 文本提取：PDF → 长字符串（10万字）
        ↓
2. Chunking：切成 500 字一段，相邻段重叠 50 字
        → [chunk_a, chunk_b, chunk_c, ...]
        ↓
3. Embedding：用 Embedding 模型把每个 chunk 转成高维向量
        → [vec_A, vec_B, vec_C, ...]
        ↓
4. 存储：把 (chunk_text, vector) 存入向量数据库
        ↓
5. 用户提问："雅思 Part2 怎么准备？"
        ↓
6. 检索：把问题也转成向量，找最相似的 Top-K 个 chunk
        → "Part2 答题结构技巧"、"Part2 常见话题分类"...
        ↓
7. 生成：把 Top-K chunk 塞进 Prompt，大模型基于知识回答
```

### D.1.1 文本切片（Chunking）

长文档不能直接传给 Embedding 模型，因为：
- 模型有最大输入长度限制（通常 512~8192 tokens）
- 太长会导致语义稀释，向量表示不精确

**切片策略**：
- **Chunk Size**：每段固定长度，如 500 字符
- **Overlap**：相邻两段保留 50 字符重叠

**为什么要重叠？**
> 防止关键句子恰好被切在边界处。例如"雅思口语考试分为三个部分，其中 Part2 是"——如果不重叠，前半句在一个 chunk 末尾，后半句在下一个 chunk 开头，语义就被割裂了。

### D.1.2 向量化（Embedding）

**Embedding 不是用大模型（ChatGPT/DeepSeek）做的，而是用专门的 Embedding 模型。**

| | **大模型（LLM）** | **Embedding 模型** |
|---|---|---|
| **输入** | 文本 | 文本 |
| **输出** | 自然语言回复 | 高维数字向量（768/1536 维） |
| **作用** | 理解、推理、生成 | 把语义压缩成数学向量 |
| **常见模型** | GPT-4、DeepSeek-V3 | `text-embedding-3-small`、`bge-m3` |

**代码示例**：

```python
from langchain_openai import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 把 "雅思口语考试技巧" 转成 1536 维向量
vector = embeddings.embed_query("雅思口语考试技巧")

print(len(vector))  # 1536
print(vector[:5])   # [0.012, -0.034, 0.008, ...]
```

**核心原理**：
- Embedding 模型用 Transformer 把句子中的词编码成数字
- 通过注意力机制，把整句话的语义"凝聚"成一个固定长度的向量
- **语义相近的文本，向量在空间中距离越近**

经典例子：
```
向量("国王") - 向量("男人") + 向量("女人") ≈ 向量("女王")
向量("雅思口语") 与 向量("IELTS speaking") 距离很近
向量("雅思口语") 与 向量("红烧排骨") 距离很远
```

---

## D.2 向量相似度检索

把用户问题也转成向量后，需要计算它与知识库中所有 chunk 向量的"相似程度"，找出最相关的 Top-K。

### 常用相似度度量

| 度量方式 | 通俗解释 | 公式特点 |
|---|---|---|
| **余弦相似度（Cosine Similarity）** | 看两个向量的"夹角"，夹角越小越相似 | **最常用**，范围 [-1, 1]，只关心语义方向 |
| **欧氏距离（Euclidean Distance）** | 两个向量端点的直线距离 | 关心绝对数值差异 |
| **点积（Dot Product）** | 对应位置相乘再求和 | 某些向量库优化后检索更快 |

```python
import numpy as np

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

question_vec = embeddings.embed_query("怎么准备雅思口语？")
sim_a = cosine_similarity(question_vec, vector_a)  # 0.89
sim_b = cosine_similarity(question_vec, vector_b)  # 0.34
```

检索时，向量数据库会预先建好**向量索引**（如 HNSW、IVFFlat），避免每次都要和百万个向量逐一计算，从而将检索时间从秒级降到毫秒级。

---

## D.3 向量数据库对比：LanceDB vs PostgreSQL + pgvector

| 维度 | **LanceDB** | **PostgreSQL + pgvector** |
|---|---|---|
| **定位** | 专用轻量级向量数据库（教学/原型/本地） | 通用数据库 + 向量扩展（生产/平台级） |
| **安装成本** | 极低，`pip install lancedb` 即可 | 需要安装 PostgreSQL 服务端 |
| **数据类型支持** | 只擅长向量数据 | 结构化数据 + 向量数据统一存储 |
| **SQL 支持** | 有限 | 完整 SQL 支持，事务、权限、备份成熟 |
| **Django ORM 集成** | 需手写查询代码 | `django.contrib.postgres` 原生支持 |
| **多用户/高并发** | 弱（本地文件锁） | 强（MVCC、连接池） |
| **LangGraph Checkpointer** | 不支持 | 官方提供 `PostgresSaver` |
| **适用阶段** | **课程学习、本地 Demo** | **MVP 部署、面试项目、生产环境** |

### LanceDB 使用示例

```python
import lancedb

db = lancedb.connect("./my_lancedb")
table = db.create_table("docs", data=[
    {"text": "雅思 Part1 技巧", "vector": vec_a},
    {"text": "雅思 Part2 技巧", "vector": vec_b},
])

# 搜索最相似的 3 条
results = table.search(question_vec).limit(3).to_list()
```

### PostgreSQL + pgvector 使用示例

```sql
-- 安装扩展
CREATE EXTENSION vector;

-- 建表
CREATE TABLE knowledge_chunks (
    id SERIAL PRIMARY KEY,
    bot_id INT NOT NULL,
    text TEXT,
    embedding vector(1536)
);

-- 建 HNSW 向量索引
CREATE INDEX idx_knowledge_embedding ON knowledge_chunks 
USING hnsw (embedding vector_cosine_ops);

-- 相似度搜索
SELECT text, embedding <=> '[0.01, -0.02, ...]' AS distance
FROM knowledge_chunks
WHERE bot_id = 123
ORDER BY embedding <=> '[0.01, -0.02, ...]'
LIMIT 3;
```

---

## D.4 Django ORM 选择不同数据库有多大区别？

**结论是：对 80% 的 CRUD 操作几乎没有区别，但对 20% 的高级特性差别很大。**

### 无差别的部分（通用 CRUD）

```python
# 这些代码在 SQLite、MySQL、PostgreSQL 下完全一样
User.objects.create(username='tom')
Message.objects.filter(friend_id=123).order_by('-id')[:10]
```

Django ORM 的 `QuerySet` 会自动把 Python 方法调用翻译成对应数据库的 SQL 方言。

### 有差别的部分（决定选 PostgreSQL 的原因）

| 特性 | SQLite | MySQL | PostgreSQL |
|---|---|---|---|
| `JSONField` 完整查询 | 基础支持 | 中等 | **最强**（底层 JSONB + GIN 索引） |
| 数组类型（`ArrayField`） | ❌ | ❌ | ✅ |
| 向量扩展（pgvector） | ❌ | ❌ | ✅ |
| `pg_trgm` 模糊搜索 | ❌ | ❌ | ✅ |
| 全文搜索（中文分词） | ❌ | ❌ | 需插件 |
| LangGraph `PostgresSaver` | ❌ | ❌ | ✅ |

**在你的 Bot 平台项目中**：
- **SQLite**：MVP 本地开发可以用，但无法支持 RAG 向量检索、没有官方 Checkpointer
- **MySQL**：不支持 pgvector，JSON 查询能力也不如 PostgreSQL
- **PostgreSQL**：**唯一一个**能同时满足"结构化数据 + 向量检索 + JSONB + Checkpointer"的开源数据库

### 推荐路径

| 阶段 | 数据库 | 理由 |
|---|---|---|
| **本地开发** | SQLite | 零配置，快速验证业务逻辑 |
| **MVP 部署/面试演示** | PostgreSQL | 展示工程化意识，为 RAG 和长期记忆铺路 |
| **二期加 RAG** | PostgreSQL + pgvector | 向量检索原生支持，无需引入额外服务 |

---

## D.5 面试话术

> "RAG 的核心流程分为三步：首先对长文档做 **Chunking**，按固定长度切片并保留重叠边界，防止语义断裂；然后通过 **Embedding 模型**（如 OpenAI 的 text-embedding-3-small）将文本段转换为高维向量，语义相近的文本在向量空间中距离更近；最后用户提问时，将问题也向量化，通过 **余弦相似度** 在向量库中检索最相关的 Top-K 片段，作为上下文注入 Prompt 供大模型生成回答。在数据库选型上，本地学习阶段可以使用 LanceDB 快速验证，但部署到平台时我选择了 PostgreSQL + pgvector，因为它能统一支撑结构化数据、JSONB 配置、向量检索和 LangGraph 的会话持久化。"

---

# 附录 E：数据库索引知识补充

> 本节记录索引的本质、类型、使用场景和底层原理，帮助在实际开发中做出正确的索引决策。

---

## E.1 索引的本质

**索引就是数据库的"目录"。**

想象一本 1000 页的电话簿：
- **没有索引**：找"张三"要从第 1 页翻到第 1000 页
- **有索引**：直接翻到"Z"开头的目录页，快速定位

数据库索引以**额外的存储空间和写入开销**为代价，换取**查询速度的指数级提升**。

---

## E.2 索引的常见类型

### 按数据结构分（底层实现）

| 类型 | 特点 | 适用场景 |
|------|------|---------|
| **B+Tree** | 最常用，支持等值、范围、排序查询 | `=`、`>`、`<`、`BETWEEN`、`ORDER BY`、`LIKE 'abc%'` |
| **Hash** | 只支持精确等值匹配，速度极快 | `=`（如缓存键查询） |
| **Bitmap** | 位图存储，适合低基数列 | 数据仓库、性别/状态等枚举值 |
| **GiST / GIN** | PostgreSQL 特有，适合全文/JSON/地理数据 | `JSONB`、`tsvector`、PostGIS |
| **HNSW / IVFFlat** | 向量索引，近似最近邻搜索 | 向量相似度检索（RAG） |

### 按功能分（SQL 层面）

| 类型 | 说明 | 例子 |
|------|------|------|
| **主键索引** | 唯一标识每行，自动创建 | `id SERIAL PRIMARY KEY` |
| **唯一索引** | 保证列值不重复 | `UNIQUE(email)` |
| **普通索引** | 加速查询，无唯一性约束 | `CREATE INDEX idx_name ON users(name)` |
| **组合索引** | 多列联合索引，遵循**最左前缀原则** | `CREATE INDEX idx_a_b ON t(a, b)` |
| **覆盖索引** | 索引包含查询所需全部列，无需回表 | `INDEX(a, b)` 查 `SELECT a, b FROM ...` |
| **全文索引** | 用于文本搜索 | PostgreSQL `GIN` + `tsvector` |

---

## E.3 什么时候该建索引？

### ✅ 应该建索引的场景

| 场景 | 原因 |
|------|------|
| 查询很频繁的列 | 如 `user_id`、`friend_id` |
| `WHERE` 条件的列 | 如 `WHERE status = 'active'` |
| `JOIN` / 外键关联的列 | 如 `Message.friend_id` 关联 `Friend.id` |
| `ORDER BY` / `GROUP BY` 的列 | 避免文件排序（filesort） |
| 数据量超过 10 万行 | 小表全表扫描很快，大表必须靠索引 |
| 低更新、高查询的表 | 索引维护成本低 |

### ❌ 不应该建索引的场景

| 场景 | 原因 |
|------|------|
| 数据量很小的表（< 1000 行） | 全表扫描比走索引还快 |
| 频繁写入、很少查询的表 | 每次写入都要维护索引，拖慢性能 |
| 区分度很低的列 | 如 `gender`（只有男/女），过滤效果差 |
| 经常参与计算的列 | 如 `WHERE age + 1 = 18`，索引失效 |
| 大文本/大二进制字段 | 建索引体积巨大 |

### 实际判断流程

```
遇到慢查询？
    ↓
用 EXPLAIN ANALYZE 看执行计划
    ↓
发现是全表扫描（Seq Scan）或扫描行数很大？
    ↓
看 WHERE / JOIN / ORDER BY 用了哪些列
    ↓
这些列区分度高吗？
    ↓
这张表写入频繁吗？
    ↓
建索引 → 再次 EXPLAIN ANALYZE 验证
```

---

## E.4 B+Tree 索引的底层原理

B+Tree 是数据库最常用的索引结构，核心特点：

```
                [10, 30, 50]              ← 根节点
               /     |     \
        [2,5,8]  [15,20,25]  [35,40,45]   ← 内部节点（导航）
       /  |  \    /  |  \    /  |  \
    数据页 数据页 数据页 数据页 数据页 数据页  ← 叶子节点（存真实数据或地址）
```

- **所有数据都在叶子节点**，内部节点只存导航键值
- **叶子节点之间用链表相连**，范围查询非常快
- **树高通常只有 3-4 层**，找一条数据最多 3-4 次磁盘 I/O

---

## E.5 聚簇索引 vs 非聚簇索引

| | **聚簇索引（Clustered）** | **非聚簇索引（Secondary）** |
|---|---|---|
| **叶子节点存储** | 存**整行数据** | 存**索引列 + 主键 ID** |
| **数量** | 一个表只能有 **1 个** | 一个表可以有 **多个** |
| **典型例子** | InnoDB 的主键索引 | InnoDB 的普通索引、PostgreSQL 的所有索引 |
| **查询过程** | 直接拿到整行 | 先找到主键 ID，再**回表**查整行（覆盖索引时无需回表） |

---

## E.6 长文本/换行文本的搜索方案：pg_trgm + GIN

普通 B-tree 索引对 `LIKE '%关键词%'` 无效，因为 `%` 在前缀时无法利用有序性。对于长文本（如聊天记录）的模糊搜索，PostgreSQL 提供了 `pg_trgm` 扩展。

### 原理

`pg_trgm` 将文本拆成**连续三个字符**（trigram），对这些 trigram 建 **GIN 索引**，从而支持中间模糊匹配。

### 建索引

```sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX idx_message_output_trgm ON message USING GIN (output gin_trgm_ops);
```

### Django 中使用

```python
from django.contrib.postgres.indexes import GinIndex

class Message(models.Model):
    output = models.TextField()

    class Meta:
        indexes = [
            GinIndex(fields=['output'], name='msg_output_trgm', opclasses=['gin_trgm_ops']),
        ]

# 查询
Message.objects.filter(output__icontains='雅思口语')
```

**效果**：`__icontains` 会自动走 GIN 索引，支持包含换行符的大文本模糊搜索。

---

## E.7 一个完整的实际案例

### 表结构

```sql
CREATE TABLE message (
    id BIGSERIAL PRIMARY KEY,
    friend_id INT NOT NULL,
    user_message TEXT,
    output TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 常见查询

```sql
SELECT * FROM message 
WHERE friend_id = 123 
ORDER BY id DESC 
LIMIT 10;
```

### 优化前

```
Seq Scan on message  (cost=0.00..1234.56 rows=999999)
  Filter: (friend_id = 123)
```

### 优化后

```sql
-- 组合索引：friend_id + 倒序 created_at
CREATE INDEX idx_message_friend_created ON message(friend_id, created_at DESC);
```

```
Index Scan using idx_message_friend_created
  Index Cond: (friend_id = 123)
```

数据库直接定位到 `friend_id=123` 的数据块，且内部已按时间排好序，直接取前 10 条。

---

## E.8 面试话术

> "在数据库设计上，我遵循'先分析再建索引'的原则。遇到慢查询时，我会先用 `EXPLAIN ANALYZE` 查看执行计划，如果发现是全表扫描，再结合查询的 `WHERE`、`JOIN`、`ORDER BY` 条件，在区分度高、查询频繁的列上建索引。对于大文本的模糊搜索，普通 B-tree 索引无法支持 `LIKE '%关键词%'`，我使用了 PostgreSQL 的 `pg_trgm` 扩展配合 GIN 索引来解决。同时我也清楚索引的 trade-off：它会增加写入开销和存储占用，所以小表、低区分度列、频繁写入的表我不会盲目加索引。"


---

# 附录 F：RabbitMQ 与消息队列知识补充

> 本节记录消息队列（Message Queue）的核心概念、RabbitMQ 的工作原理，以及在 AI 应用平台中的典型使用场景和扩展规划。

---

## F.1 为什么需要消息队列？

在单体应用中，请求通常是同步处理的：用户点击按钮 → 后端立即执行 → 返回结果。但当遇到以下场景时，同步处理会导致用户体验差、系统耦合高、容易崩溃：

| 问题 | 举例 | 消息队列的解决方式 |
|------|------|-------------------|
| **执行耗时太长** | 上传 100 页 PDF 做 RAG 解析，需要 30 秒 | 把任务扔到队列，后台异步处理，前端立刻返回"正在处理中" |
| **流量突发高峰** | 1000 个用户同时请求大模型 API | 把请求排队，按固定速率消费，避免打爆上游 API |
| **服务间强耦合** | 用户注册后要同时发邮件、更新统计、通知推荐系统 | 注册服务只发一条消息到队列，其他服务各自独立消费 |
| **任务需要重试** | 调用第三方 API 偶尔失败 | 消费失败后将消息重新放回队列，自动重试 3 次 |

**一句话：消息队列让"发送任务"和"执行任务"在时间和空间上解耦。**

---

## F.2 RabbitMQ 核心概念

RabbitMQ 是最主流的开源消息队列之一，基于 AMQP 协议。理解以下 7 个概念就能上手：

### 1. Producer（生产者）
发送消息的应用程序。

```python
import pika

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()
channel.basic_publish(exchange='', routing_key='hello', body='Hello World!')
```

### 2. Consumer（消费者）
接收并处理消息的应用程序。消费者通常以长连接方式持续监听队列。

```python
def callback(ch, method, properties, body):
    print(f"Received {body}")

channel.basic_consume(queue='hello', on_message_callback=callback, auto_ack=True)
channel.start_consuming()
```

### 3. Queue（队列）
消息的缓冲区。生产者把消息发到队列，消费者从队列中取消息。

### 4. Exchange（交换机）
生产者不直接发消息到队列，而是发到 **Exchange**，由 Exchange 决定消息路由到哪个队列。

| Exchange 类型 | 路由规则 | 适用场景 |
|--------------|---------|---------|
| **Direct** | `routing_key` 完全匹配 | 点对点精确投递，如"发给邮件服务" |
| **Fanout** | 广播到所有绑定的队列 | 群发通知，如"用户注册后广播给统计和日志服务" |
| **Topic** | `routing_key` 按模式匹配（支持 `*` 和 `#`） | 灵活路由，如`order.created.us`、`order.created.cn` |
| **Headers** | 根据消息 headers 的键值对匹配 | 复杂条件路由，较少用 |

### 5. Routing Key（路由键）
生产者发送消息时附带的一个字符串，Exchange 根据它来决定消息去往哪个 Queue。

### 6. Binding（绑定）
Exchange 和 Queue 之间的关联规则。比如：
> "`email_exchange`（Direct）把所有 `routing_key='send_email'` 的消息路由到 `email_queue`"

### 7. Acknowledgment（ACK 确认机制）
消费者处理完消息后，向 RabbitMQ 发送 **ack**。如果消费者崩溃或处理失败，RabbitMQ 会在一段时间后把消息**重新投递**给其他消费者。

```python
# auto_ack=False 表示手动确认
channel.basic_consume(queue='task_queue', on_message_callback=callback, auto_ack=False)

def callback(ch, method, properties, body):
    try:
        process_task(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)  # 成功确认
    except Exception:
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  # 失败重试
```

---

## F.3 进阶特性

### 持久化（Durability）
防止 RabbitMQ 重启后消息丢失，需要在三个层面都开启持久化：
1. **Queue 持久化**：`durable=True`
2. **Exchange 持久化**：`durable=True`
3. **Message 持久化**：`delivery_mode=2`

### TTL（Time To Live）
消息的过期时间。超过 TTL 未被消费的消息会自动进入死信队列或被丢弃。

### 死信队列（DLX - Dead Letter Exchange）
处理以下三种"异常消息"：
- 消息被拒绝（reject/nack）且不再重试
- 消息过期（TTL 到了）
- 队列达到最大长度，溢出的消息

**用途**：把失败/过期的消息收集起来，便于后续人工审计或自动补偿。

### Prefetch Count（QoS）
控制消费者一次最多从队列中取多少条消息。防止某个消费者"贪心地"拉走大量消息，导致其他消费者空闲。

```python
channel.basic_qos(prefetch_count=1)  # 一次只取 1 条，处理完再取下一条
```

---

## F.4 在 AI Bot 平台中的典型使用场景

虽然 MVP 阶段不强制引入消息队列，但以下场景天然适合用 RabbitMQ 实现：

### 场景 1：异步 RAG 文档解析（最典型）
用户上传一个 100 页的 PDF 作为知识库。

**同步方案的弊端**：
- 后端需要等待 20-30 秒完成文本提取、切片、Embedding、入库
- 前端用户一直卡在"上传中"，体验极差
- 一旦中间某一步失败，整个请求都失败，没有重试机制

**消息队列方案**：
```
用户上传 PDF
    ↓
后端保存文件，向 RabbitMQ 发送"解析文档"任务
    ↓
立即返回：{"status": "processing", "task_id": "xxx"}
    ↓
后台 Worker 消费队列：提取 → 切片 → Embedding → 写入向量库
    ↓
前端轮询 / WebSocket 通知：解析完成
```

### 场景 2：大模型 API 流量削峰
大量用户同时和 Bot 聊天，后端调用大模型 API 时可能触发限流（rate limit）。

**消息队列方案**：
- 把用户的 LLM 请求放入 RabbitMQ 队列
- 后端 Consumer 按固定速率（如每秒 10 个）从队列中消费并调用 API
- 避免瞬间高峰打爆大模型服务商的接口

### 场景 3：解耦用户行为通知
用户创建了一个 Bot 并设为公开：
- 需要更新搜索引擎索引
- 需要给订阅者发通知
- 需要记录运营统计

**消息队列方案**：
- Bot 服务只发一条 `bot_published` 消息到 Fanout Exchange
- 搜索服务、通知服务、统计服务各自监听并独立处理
- 新增一个"推荐服务"时，只需要多绑定一个队列，不需要改动 Bot 服务

---

## F.5 Django 中如何集成 RabbitMQ

### 方式 1：Celery + RabbitMQ（最常用）
Celery 是 Python 最常用的分布式任务队列，底层可以用 RabbitMQ 作为 Broker。

```python
# settings.py
CELERY_BROKER_URL = 'amqp://user:password@localhost:5672//'

# tasks.py
from celery import shared_task

@shared_task
def process_document_task(bot_id, file_path):
    # 1. 提取文本
    # 2. 切片
    # 3. Embedding
    # 4. 写入向量库
    pass

# views.py
process_document_task.delay(bot_id, file_path)  # 异步投递到 RabbitMQ
```

### 方式 2：直接使用 pika（更轻量）
如果不需要 Celery 的复杂调度，可以直接用 `pika` 库发消息：

```python
import pika
import json

def publish_task(queue_name, payload):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(
        exchange='',
        routing_key=queue_name,
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2)  # 持久化消息
    )
    connection.close()

publish_task('rag_queue', {'bot_id': 123, 'file_path': '/tmp/x.pdf'})
```

---

## F.6 MVP 阶段是否要用 RabbitMQ？

**建议：MVP 不做，但架构上预留异步任务接口。**

| 阶段 | 建议 | 理由 |
|------|------|------|
| **MVP（4-6 周）** | 不用 RabbitMQ | 增加部署和运维复杂度，RAG 解析可以用小文件模拟快速处理 |
| **二期（有用户后）** | 引入 Celery + RabbitMQ | 处理大文件解析、批量 Embedding、邮件通知等异步任务 |

**MVP 阶段的简化方案**：
- 文档解析：限制上传文件大小（如 1MB 以内），同步处理即可
- 大模型调用：直接 SSE 流式返回，不经过队列
- 通知/统计：先同步写入数据库，后续再迁移到消息队列

---

## F.7 面试话术

> "在平台架构设计上，我预留了消息队列的扩展位。比如用户上传知识库文档时，RAG 解析过程可能耗时数十秒，MVP 阶段我采用同步处理加文件大小限制的方式快速验证；当用户量和文档规模上来后，我会引入 **RabbitMQ + Celery** 做异步任务队列，将文档解析、Embedding、向量入库等重任务从主请求链路中解耦，同时利用队列的 QoS 和 ACK 机制实现流量削峰和失败重试。"

---

**总结：RabbitMQ 是构建高可用、可扩展 AI 平台的重要基础设施，但 MVP 阶段应保持简单，优先把核心链路跑通，消息队列作为明确的二期扩展路径。**


---

# 附录 G：Elasticsearch 集成规划（知识补充）

> 本节记录 Elasticsearch（ES）的核心原理、与 PostgreSQL 的定位差异，以及在 AI Bot 平台中的搜索场景设计和集成方案。

---

## G.1 为什么要引入 Elasticsearch？

PostgreSQL 擅长**结构化数据的增删改查和关联查询**，但在**大规模全文搜索、模糊匹配、聚合分析**方面能力有限。随着 Bot 广场中的公开 Bot 数量增长、用户聊天记录累积，以下场景会迅速成为性能瓶颈：

| 场景 | PostgreSQL 的问题 | Elasticsearch 的优势 |
|------|-------------------|---------------------|
| **Bot 广场搜索** | `LIKE '%雅思%'` 全表扫描，10 万条 Bot 时查询超过 1 秒 | 毫秒级返回，支持分词、拼音、同义词、高亮 |
| **聊天记录检索** | 用户想搜"上周提到的考试时间"，涉及时间+文本混合条件 | 支持时间范围 + 全文检索的复合过滤 |
| **用户行为分析** | 统计"最近 7 天最受欢迎的 Bot" | 内置强大的聚合（Aggregation）能力 |
| **日志排查** | 排查某个 Workflow Bot 的执行异常日志 | 支持海量日志的实时检索和可视化 |

**一句话：PostgreSQL 是"数据库"，Elasticsearch 是"搜索引擎"。两者分工协作，不可互相替代。**

---

## G.2 Elasticsearch 核心概念

| ES 概念 | 类比（关系型数据库） | 说明 |
|--------|---------------------|------|
| **Index（索引）** | Database（数据库） | 存储一类文档的集合，如 `bot_index`、`message_index` |
| **Type（类型）** | Table（表） | ES 7.x 后已废弃，一个 Index 只有一个默认 `_doc` |
| **Document（文档）** | Row（行） | 一条 JSON 格式的数据记录 |
| **Field（字段）** | Column（列） | 文档中的某个属性，如 `name`、`description` |
| **Mapping（映射）** | Schema（表结构） | 定义字段的数据类型（`text`、`keyword`、`date`、`integer`） |
| **Shard（分片）** | 数据分区 | 一个 Index 的数据被水平拆分到多个 Shard，支持分布式存储和并行查询 |
| **Replica（副本）** | 主从复制 | Shard 的复制，提高可用性和读取性能 |

### 核心原理：倒排索引（Inverted Index）

关系型数据库的索引通常是"文档 ID → 内容"的正向索引。ES 使用的是**倒排索引**：

```
正向索引：          倒排索引（ES）：
Doc1: 雅思口语      雅思    → Doc1, Doc3
Doc2: 红烧排骨      口语    → Doc1, Doc3
Doc3: 雅思听力      听力    → Doc3
                    红烧    → Doc2
                    排骨    → Doc2
```

**优势**：搜索"雅思"时，不需要扫描所有文档，直接去倒排索引里查"雅思"对应的文档列表即可，复杂度从 O(N) 降到 O(1)。

---

## G.3 在 AI Bot 平台中的搜索场景设计

### 场景 1：Bot 广场的全文搜索（最核心）

用户在广场顶部的搜索框输入"雅思口语专家"，需要快速从公开 Bot 中找到匹配项。

**搜索维度**：
- Bot 名称（`name`）
- Bot 描述（`description`）
- Bot 创建者昵称（`creator_name`）
- System Prompt 内容（`system_prompt`）

**ES 查询示例**：

```json
GET /bot_index/_search
{
  "query": {
    "multi_match": {
      "query": "雅思口语专家",
      "fields": ["name^3", "description^2", "system_prompt"],
      "type": "best_fields"
    }
  },
  "highlight": {
    "fields": {
      "description": {}
    }
  }
}
```

> `^3` 表示 `name` 字段的权重是 3 倍，命中名称的 Bot 会排在更前面。

### 场景 2：用户聊天记录检索

用户想和某个 Bot 聊了 1000 条消息，想快速找到"上周说的考试时间"。

**ES 文档设计**：

```json
{
  "message_id": 12345,
  "session_id": "uuid-xxx",
  "friend_id": 100,
  "user_id": 50,
  "role": "user",
  "content": "我打算下个月 15 号参加雅思考试",
  "created_at": "2024-05-10T14:30:00Z"
}
```

**复合查询**：时间范围 + 全文搜索 + 精确过滤

```json
GET /message_index/_search
{
  "query": {
    "bool": {
      "must": [
        { "match": { "content": "考试时间" } },
        { "range": { "created_at": { "gte": "now-7d/d" } } }
      ],
      "filter": [
        { "term": { "user_id": 50 } },
        { "term": { "friend_id": 100 } }
      ]
    }
  }
}
```

### 场景 3：热门 Bot 聚合统计

运营后台需要看"最近 7 天被添加到个人列表次数最多的 Top 10 Bot"。

```json
GET /binding_index/_search
{
  "size": 0,
  "query": {
    "range": { "created_at": { "gte": "now-7d/d" } }
  },
  "aggs": {
    "top_bots": {
      "terms": {
        "field": "bot_id",
        "size": 10
      }
    }
  }
}
```

---

## G.4 Elasticsearch 与 RAG / 向量搜索的关系

这是一个非常容易混淆的点，三者分工如下：

| 技术 | 解决的问题 | 搜索方式 | 例子 |
|------|-----------|---------|------|
| **PostgreSQL + B-tree** | 精确条件过滤 | `WHERE id = 123` | 查某个用户的个人信息 |
| **Elasticsearch** | 关键词全文搜索、聚合分析 | "雅思口语" → 找到包含这些词的文档 | 在 Bot 广场搜索"雅思" |
| **pgvector / RAG** | 语义相似度搜索 | "怎么练口语？" → 找到"雅思 Part2 技巧" | 基于用户问题检索相关知识库 |

**关键区别**：
- ES 搜索的是**字面匹配**（你搜"雅思"，它找包含"雅思"这个词的文档）。
- RAG / 向量搜索的是**语义匹配**（你搜"怎么练口语"，它找到"雅思口语技巧"，即使文档里没有"怎么练"这几个字）。

**在项目中建议组合使用**：
- Bot 广场搜索 → **Elasticsearch**（用户明确输入了关键词）
- 知识库 RAG 检索 → **pgvector**（用户问题和知识片段的语义匹配）

---

## G.5 Django 中集成 Elasticsearch 的方案

### 方案 1：直接使用 `elasticsearch-py`（最灵活，推荐）

不依赖 Django ORM，直接在视图/服务层调用 ES。

```python
from elasticsearch import Elasticsearch

es = Elasticsearch(['http://localhost:9200'])

# 创建索引并定义 Mapping
es.indices.create(
    index='bot_index',
    body={
        "mappings": {
            "properties": {
                "name": { "type": "text", "analyzer": "ik_max_word" },
                "description": { "type": "text", "analyzer": "ik_max_word" },
                "creator_name": { "type": "keyword" },
                "is_public": { "type": "boolean" },
                "created_at": { "type": "date" }
            }
        }
    }
)

# 写入文档
doc = {
    "name": "雅思口语专家",
    "description": "帮助你练习雅思口语，提供实时反馈",
    "creator_name": "Tom",
    "is_public": True,
    "created_at": "2024-06-01T00:00:00Z"
}
es.index(index='bot_index', id=1, body=doc)

# 搜索
response = es.search(index='bot_index', body={
    "query": {
        "multi_match": {
            "query": "雅思口语",
            "fields": ["name^3", "description^2"]
        }
    }
})
hits = response['hits']['hits']
```

### 方案 2：`django-haystack`（ORM 集成度高，但较重）
`django-haystack` 提供了一个统一的搜索抽象层，底层可以切换 ES、Whoosh、Solr 等。但学习成本较高，且对 ES 新特性的支持往往滞后。

### 方案 3：信号自动同步（数据一致性保障）

Django 中使用 `post_save` 和 `post_delete` 信号，保证 PostgreSQL 和 ES 的数据一致：

```python
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Bot

@receiver(post_save, sender=Bot)
def sync_bot_to_es(sender, instance, **kwargs):
    if instance.is_public:
        es.index(index='bot_index', id=instance.id, body={
            "name": instance.name,
            "description": instance.description,
            "is_public": instance.is_public,
            "created_at": instance.created_at.isoformat()
        })
    else:
        # 设为私有时从 ES 删除
        es.delete(index='bot_index', id=instance.id, ignore=[404])

@receiver(post_delete, sender=Bot)
def remove_bot_from_es(sender, instance, **kwargs):
    es.delete(index='bot_index', id=instance.id, ignore=[404])
```

---

## G.6 中文分词：为什么要装 IK 分词器？

Elasticsearch 默认的标准分词器（Standard Analyzer）对中文是按**单字**切的：

```
"雅思口语专家" → [雅, 思, 口, 语, 专, 家]
```

这会导致搜索"口语"时，匹配到所有包含"口"或"语"的文档，精度很差。

**IK 分词器**是 ES 最流行的中文分词插件，支持两种模式：
- `ik_max_word`：最细粒度切分（"雅思口语专家" → [雅思, 雅思口语, 口语, 专家, 雅思口语专家]）
- `ik_smart`：最粗粒度切分（"雅思口语专家" → [雅思口语, 专家]）

**建议**：索引时用 `ik_max_word`（保证召回率），搜索时用 `ik_smart`（保证精确度）。

```json
{
  "mappings": {
    "properties": {
      "name": {
        "type": "text",
        "analyzer": "ik_max_word",
        "search_analyzer": "ik_smart"
      }
    }
  }
}
```

---

## G.7 MVP 阶段是否集成 Elasticsearch？

**明确建议：MVP 不做，但架构和字段设计要预留。**

| 阶段 | 建议 | 搜索实现方式 |
|------|------|-------------|
| **MVP（0-1000 个 Bot）** | 不用 ES | PostgreSQL 的 `__icontains` 足够 |
| **增长期（1 万 + Bot）** | 引入 ES | Bot 广场全文搜索、聊天记录检索 |
| **成熟期** | ES + pgvector 双引擎 | ES 做关键词搜索，pgvector 做语义搜索 |

**MVP 阶段的简化方案**：
- Bot 广场搜索：先用 PostgreSQL `name__icontains` 或 `description__icontains`
- 聊天记录搜索：暂时不支持全局搜索，只按 `friend_id` 分页加载
- 运营统计：直接 Django ORM `annotate` + `Count`

---

## G.8 面试话术

> "在平台的数据架构上，我采用 **PostgreSQL + Elasticsearch 双引擎**的设计。PostgreSQL 负责事务性数据的强一致性存储，如用户、Bot 配置、聊天记录；Elasticsearch 负责全文搜索和聚合分析，如 Bot 广场的关键词检索、用户聊天记录的历史搜索、以及热门 Bot 的运营统计。对于语义层面的知识检索，则由 **pgvector** 向量库负责。三者各司其职，共同支撑平台的查询和分析需求。"

---

**总结：Elasticsearch 是 AI Bot 平台从"能用"走向"好用"的关键基础设施，主要负责关键词全文搜索和数据分析。MVP 阶段可用 PostgreSQL 的模糊查询简化替代，但面试时展现出"PG + ES + 向量库"的三层架构思维是明显的加分项。**
