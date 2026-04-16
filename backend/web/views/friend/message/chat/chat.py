import asyncio
import base64
import os
from queue import Queue
import threading
from uuid import uuid4

from django.http import StreamingHttpResponse
from typing import Generator, Any

from django.utils.timezone import now
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer

from langchain_core.messages import HumanMessage, AIMessage, BaseMessageChunk, AIMessageChunk, SystemMessage

import json

import websockets

from web.models.friend import Friend, Message, Session, SystemPrompt
from web.views.friend.message.chat.graph import AgentState, ChatGraph
from web.views.friend.message.memory.update import update_memory
from web.views.friend.message.session_name.update import update_session_name


class SSERenderer(BaseRenderer):
    """自定义 SSE 渲染器，使 DRF 能正确返回 text/event-stream 格式"""
    media_type = 'text/event-stream'
    format = 'txt'
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data


def add_system_prompt(state, friend) -> AgentState:
    """
    组装系统提示词：从数据库读取通用模板后，再拼接角色身份、性格和长期记忆。

    2026-04 改动：
        - 若 Character 被删除，仍可从 Friend 快照字段中读取角色信息。
        - 显式告诉 AI"你是谁"，防止 AI 把角色名误当成用户名。
    """
    msgs = state['messages']
    system_prompts = SystemPrompt.objects.filter(title='回复').order_by('order_number')
    prompt = ''
    for sp in system_prompts:
        prompt += sp.prompt
    character_name = friend.character_name or (friend.character.name if friend.character else '未知角色')
    profile = friend.character_profile or (friend.character.profile if friend.character else '')
    prompt += f'\n你的名字是{character_name}，你要扮演这个角色。用户正在和你聊天，请始终从{character_name}的视角进行回复。\n'
    prompt += f'【角色性格】\n{profile}\n'
    prompt += f'【长期记忆】\n{friend.memory}\n'
    return {'messages': [SystemMessage(prompt)] + msgs}


def add_recent_messages(state, session) -> AgentState:
    """
    把当前 Session 的最近 10 条消息拼接成 LangChain Message 列表。

    2026-04 修复：
        - 开场白消息的 user_message 为空字符串，如果直接生成 HumanMessage('')，
          会把空用户消息拼进 prompt，导致 AI 行为异常。
        - 因此加了 if m.user_message 判断，只把非空用户消息加入上下文。
    """
    msgs = state['messages']
    message_raw = list(Message.objects.filter(session=session).order_by('-id')[:10])
    message_raw.reverse()
    messages = []
    for m in message_raw:
        if m.user_message:
            messages.append(HumanMessage(m.user_message))
        messages.append(AIMessage(m.output))
    return {'messages': msgs[:1] + messages + msgs[-1:]}


class MessageChatView(APIView):
    """
    CHAT /api/friend/message/chat/

    2026-04 核心改动：
        - 校验从 Message.friend 改为 Session.friend，适应新的多会话架构。
        - 增加安全拦截：角色被删除后，已有 Session 只能查看历史，不能再发起新对话。
        - 流式返回通过 SSE（Server-Sent Events）实现，同时把 AI 返回的文本实时转发给
          阿里云百炼 TTS WebSocket，实现"边说边播"的语音体验。
    """
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
        # 安全拦截：角色被删除后禁止继续对话
        if not friend.character:
            return Response({'result': '该角色已被删除，无法继续对话'})

        app = ChatGraph.create_app()
        inputs: AgentState = {
            'messages': [HumanMessage(content=message)]
        }
        inputs = add_system_prompt(inputs, friend)
        inputs = add_recent_messages(inputs, session)

        response = StreamingHttpResponse(
            self.event_stream(app, inputs, friend, session, message),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        # 避免 nginx 等反向代理缓存 SSE
        response['X-Accel-Buffering'] = 'no'
        return response

    async def tts_sender(self, app, inputs, mq, ws, task_id, stop_event):
        """
        发送 AI 生成的文本片段到阿里云百炼 TTS WebSocket。
        同时把文本内容和 usage_metadata 放入线程安全队列 mq，供主线程消费并 SSE 推送给前端。
        若 stop_event 被设置（前端断开连接），则立即停止生成，但仍需发送 finish-task 结束任务。
        """
        async for msg, metadata in app.astream(inputs, stream_mode="messages"):
            if stop_event.is_set():
                break
            if isinstance(msg, BaseMessageChunk):
                if msg.content:
                    await ws.send(json.dumps({
                        "header": {
                            "action": "continue-task",
                            "task_id": task_id,
                            "streaming": "duplex"
                        },
                        "payload": {
                            "input": {
                                "text": msg.content
                            }
                        }
                    }))
                    mq.put_nowait({'content': msg.content})

                if isinstance(msg, AIMessageChunk) and hasattr(msg, 'usage_metadata') and msg.usage_metadata:
                    mq.put_nowait({'usage': msg.usage_metadata})

        # 通知 TTS 服务结束本次任务（无论正常结束还是中断都必须发送，否则超时/计费异常）
        await ws.send(json.dumps({
            "header": {
                "action": "finish-task",
                "task_id": task_id,
                "streaming": "duplex"
            },
            "payload": {
                "input": {}  # input 不能省去，否则会报错
            }
        }))

    async def tts_receiver(self, mq, ws):
        """接收阿里云百炼 TTS 返回的音频二进制数据，base64 编码后放入队列"""
        async for msg in ws:
            if isinstance(msg, bytes):
                audio = base64.b64encode(msg).decode('utf-8')
                mq.put_nowait({'audio': audio})
            else:
                data = json.loads(msg)
                event = data['header']['event']
                if event in ['task-finished', 'task-failed']:
                    break

    # 语音合成
    # 阿里云TTS文档：https://bailian.console.aliyun.com/cn-beijing/?spm=5176.12818093_47.console-base_product-drawer-right.dproducts-and-services-sfm.258b16d0dZyCzu&tab=api#/api/?type=model&url=2853143
    async def run_tts_tasks(self, app, inputs, mq, stop_event):
        """
        语音合成主协程：
        建立 WebSocket 连接 -> 发送 run-task -> 等待 task-started ->
        并发运行 tts_sender（送文本）和 tts_receiver（收音频）。
        """
        task_id = uuid4().hex
        api_key = os.getenv('API_KEY')
        wss_url = os.getenv('WSS_URL')
        if not api_key or not wss_url:
            raise ValueError('缺少 API_KEY 或 WSS_URL 环境变量')
        headers = {
            'Authorization': f"Bearer {api_key}"
        }
        async with websockets.connect(wss_url, additional_headers=headers) as ws:
            await ws.send(json.dumps({
                "header": {
                    "action": "run-task",
                    "task_id": task_id,
                    "streaming": "duplex"
                },
                "payload": {
                    "task_group": "audio",
                    "task": "tts",
                    "function": "SpeechSynthesizer",
                    "model": "cosyvoice-v3-flash",
                    "parameters": {
                        "text_type": "PlainText",
                        "voice": "longanyang",          # 音色
                        "format": "mp3",                # 音频格式
                        "sample_rate": 22050,           # 采样率
                        "volume": 50,                   # 音量
                        "rate": 1.25,                   # 语速
                        "pitch": 1                      # 音调
                    },
                    "input": {}  # input 不能省去，不然会报错
                }
            }))
            async for msg in ws:
                if json.loads(msg)['header']['event'] == 'task-started':
                    break
            await asyncio.gather(
                self.tts_sender(app, inputs, mq, ws, task_id, stop_event),
                self.tts_receiver(mq, ws),
            )

    def work(self, app, inputs, mq, stop_event):
        """在新线程中运行 TTS 协程，通过队列与主线程通信"""
        try:
            asyncio.run(self.run_tts_tasks(app, inputs, mq, stop_event))
        finally:
            mq.put_nowait(None)  # 发送结束信号

    def _save_message(self, session, friend, message, inputs, full_output, full_usage):
        """将已生成的内容持久化到数据库，并更新相关时间戳与记忆。"""
        if not full_output:
            return
        input_tokens = full_usage.get('input_tokens', 0)
        output_tokens = full_usage.get('output_tokens', 0)
        total_tokens = full_usage.get('total_tokens', 0)

        Message.objects.create(
            session=session,
            user_message=message[:500],
            input=json.dumps(
                [m.model_dump() for m in inputs['messages']],
                ensure_ascii=False
            )[:10000],
            output=full_output[:500],
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens
        )
        friend.update_time = now()
        friend.save()
        session.update_time = now()
        session.save()

        # 每累计 10 条消息触发一次长期记忆更新
        if Message.objects.filter(session=session).count() % 10 == 0:
            update_memory(friend, session)

    def event_stream(self, app, inputs, friend, session, message) -> Generator[bytes, Any, None]:
        """
        SSE 事件流生成器：
          1. 启动独立线程跑 TTS（AI 生成 + 语音合成）。
          2. 主线程消费队列，把文本和音频逐段 yield 给前端。
          3. 当客户端断开（如切换/关闭会话）时，通过 stop_event 通知后台线程停止生成，
             并在 finally 里把已返回的内容写入数据库，避免数据丢失。
        """
        mq = Queue()
        stop_event = threading.Event()
        thread = threading.Thread(target=self.work, args=(app, inputs, mq, stop_event))
        thread.start()

        full_output = ''
        full_usage = {}
        saved = False

        try:
            while True:
                msg = mq.get()
                if not msg:
                    break
                if msg.get('content', None):
                    full_output += msg['content']
                    yield f'data: {json.dumps({"content": msg["content"]}, ensure_ascii=False)}\n\n'.encode('utf-8')
                if msg.get('audio', None):
                    yield f'data: {json.dumps({"audio": msg["audio"]}, ensure_ascii=False)}\n\n'.encode('utf-8')
                if msg.get('usage', None):
                    full_usage = msg['usage']

            yield 'data: [DONE]\n\n'.encode('utf-8')
        finally:
            if not saved:
                self._save_message(session, friend, message, inputs, full_output, full_usage)
                saved = True
            # 首轮对话结束后异步生成标题
            if session.session_name  == '新的对话':
                session_name_thread = threading.Thread(
                    target=update_session_name,
                    args=(session.id, message),
                    daemon=True
                )
                session_name_thread.start()
            stop_event.set()
            thread.join(timeout=2.0)
