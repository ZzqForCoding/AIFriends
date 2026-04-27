# AIFriends — AI 角色聊天系统

一个基于 Django + Vue 3 的 AI 角色聊天应用，支持流式对话、语音合成、多会话管理、RAG 知识库和长期记忆。

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

## ✨ 核心功能

### 1. AI 角色聊天
- 创建和管理多个 AI 角色（Friend），每个角色可独立配置人设、模型参数和绑定资源
- 支持角色级别的模型选择、温度（temperature）和深度思考开关配置
- 首次对话自动发送角色开场白

### 2. 流式对话与语音合成
- 使用 **SSE** 实时推送 AI 生成的文本与音频片段
- 接入 **阿里云百炼 TTS**，实现边生成边朗读的实时语音体验
- 支持前端 **AbortController 中断**：切换会话、删除会话或关闭弹窗时，后端立即停止生成并保存已产出的内容
- AI 回复支持 **Markdown 渲染**（代码块、列表、引用等样式）

### 3. 多会话与历史管理
- 每个 AI 角色支持多个 `Session`，会话列表支持滚动加载、创建与删除
- 首轮对话结束后由 AI 自动生成会话标题
- 发送消息后前端即时将会话置顶，与后端 `update_time` 排序保持一致

### 4. ReAct 工具调用
- 基于 LangGraph 的 ReAct 循环，支持模型自主决策调用工具
- 内置工具可通过「技能」机制按角色启用或关闭

### 5. RAG 知识库
- 使用 **LanceDB** 进行向量存储与检索
- 支持文档上传、切片、Embedding 和检索生成
- 知识库按角色隔离，不同角色可绑定不同的知识库

### 6. 长期记忆
- 每累计 **10 条消息**自动触发一次长期记忆总结
- 记忆内容持久化存储，跨会话保持角色对用户的了解

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
├── PROJECT_GOALS.md         # 项目规划
└── COZE_FUNCTION_ANALYSIS.md # 功能分析
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

