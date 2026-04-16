# AIFriends — 可配置 AI 智能体平台

> 一个基于 Django + Vue 3 的 AI 角色聊天系统，正在向“可配置智能体平台”演进。底层已具备 LangGraph 流式对话、ReAct 工具调用、LanceDB 向量检索和自动长期记忆，目标是在不推倒重来的前提下，让硬编码的 AI 能力变成用户可自定义的配置项。

---

## 🚀 项目定位

**AIFriends** 最初是一个固定人设的 AI 角色聊天应用。现在的演进思路是：在 `Character` 模型上增加一层配置（模型、温度、知识库、技能、工作流），使其逐步成为一个**简化版的可配置 Agent 平台**（类似 Coze 的轻量化实现）。

核心原则：
- **不推倒重来**：在现有 LangGraph 流式对话基础上做加法
- **配置即能力**：把写死的 Prompt、工具、RAG 逻辑，变成用户可开关的选项
- **默认简单，高级可用**：普通角色走内置 ReAct，高级用户可绑定自定义工作流

---

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| **前端** | Vue 3 + TypeScript + Vite + Pinia + Tailwind CSS + DaisyUI |
| **后端** | Django + Django REST Framework |
| **AI 引擎** | LangGraph + LangChain |
| **向量检索** | LanceDB |
| **语音合成** | 阿里云百炼 TTS (WebSocket) |
| **实时通信** | Server-Sent Events (SSE) |
| **语音输入** | `@ricky0123/vad-web` (浏览器端 VAD) |

---

## ✨ 已具备的核心能力

### 1. 流式对话与语音合成
- 使用 **SSE** 推送 AI 生成的文本与音频片段
- 接入 **阿里云百炼 TTS**，实现边生成边朗读的实时语音体验
- 支持前端 **AbortController 中断**：切换会话、删除会话或关闭弹窗时，后端立即停止生成并保存已产出的内容

### 2. 多会话与历史管理
- 每个 AI 角色 (`Friend`) 支持多个 `Session`
- 会话列表支持 **滚动加载**、创建与删除
- **首轮对话结束后自动生成会话标题**（调用 deepseek-v3.2）
- 发送消息后前端即时将会话置顶，与后端 `update_time` 排序保持一致

### 3. ReAct 工具调用
- 基于 LangGraph 的 ReAct 循环，支持模型自主决策调用工具
- 未来将通过“技能广场”把硬编码工具变为用户可配置项

### 4. RAG 知识库（已有基础）
- 使用 **LanceDB** 进行向量存储与检索
- 支持文档上传、切片、Embedding 和检索生成

### 5. 长期记忆
- 每累计 **10 条消息**自动触发一次长期记忆总结
- 记忆内容持久化，跨会话保持角色对用户的了解

---

## 📁 项目结构

```
AIFriends/
├── backend/                 # Django 后端
│   ├── web/                 # 主应用（模型、视图、API）
│   ├── backend/             # Django 项目配置
│   ├── media/               # 用户上传文件
│   ├── static/              # 静态资源
│   ├── manage.py
│   └── requirements.txt
├── frontend/                # Vue 3 前端
│   ├── src/
│   │   ├── components/      # 页面组件（含角色聊天、会话管理）
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── js/http/         # 请求封装（含 SSE streamApi）
│   │   └── ...
│   ├── package.json
│   └── vite.config.ts
├── tests/e2e/               # 端到端测试
├── PROJECT_GOALS.md         # 项目演进规划
└── COZE_FUNCTION_ANALYSIS.md # 功能分析与面试建议
```

---

## 🚦 快速开始

### 后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

> 需要配置环境变量 `API_KEY`、`API_BASE` 以及阿里云 TTS 相关密钥才能完整体验对话与语音功能。

---

## 🗺 演进路线

见 [`PROJECT_GOALS.md`](./PROJECT_GOALS.md)。

**核心里程碑：**

| 阶段 | 目标 | 状态 |
|------|------|------|
| 0. 体验优化 | 大聊天窗口 + Markdown 渲染 | 🚧 进行中 |
| 1. 开场白 | 首次对话自动发送欢迎语 | ✅ 已完成 |
| 1.5 历史对话 | 多会话管理、AI 自动生成标题 | ✅ 已完成 |
| 2. 模型配置 | 不同角色用不同模型/温度/深度思考 | 📋 计划中 |
| 3. 知识库 | 动态绑定 RAG | 📋 计划中 |
| 4. 技能广场 | 工具从写死变可配置 | 📋 计划中 |
| 5. 工作流 | 可视化编排 + 自定义执行路径 | 📋 计划中 |
| 6. 多模态 | 图片上传与 AI 识图 | 📋 计划中 |

---

## 💡 面试可强调的技术亮点

> “这个项目最初是固定 AI 角色系统，底层已有 **LangGraph 流式对话**、**ReAct 工具调用**、**LanceDB 检索**和**自动长期记忆**。我的演进思路是在 `Character` 上加配置层（模型、温度、知识库、技能），让硬编码能力变用户可配；同时优化基础体验（大窗口、Markdown、历史会话管理）。对于高级需求，再叠加**深度思考开关**和可选的**工作流编排**——默认走 ReAct 降低门槛，高级用户可自定义节点路径。”

---

*最后更新：2026-04-16*
