from ast import arg
import asyncio
import base64
import os
from queue import Queue
import threading
from uuid import uuid4
from warnings import catch_warnings

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

class SSERenderer(BaseRenderer):
    media_type = 'text/event-stream'
    format = 'txt'
    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data

# 组装系统提示词：从数据库读取通用模板后，再拼接角色身份、性格和长期记忆
# 注意：显式告诉 AI"你是谁"，防止 AI 把角色名误当成用户名
# 若 Character 被删除，仍可从 Friend 快照字段中读取角色信息
# TODO: 后续可考虑将身份定位模板迁移到 SystemPrompt 模型中动态配置
def add_system_prompt(state, friend) -> AgentState:
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
    msgs = state['messages']
    message_raw = list(Message.objects.filter(session=session).order_by('-id')[:10])
    message_raw.reverse()
    messages = []
    for m in message_raw:
        messages.append(HumanMessage(m.user_message))
        messages.append(AIMessage(m.output))
    return {'messages': msgs[:1] + messages + msgs[-1:]}

class MessageChatView(APIView):
    permission_classes = [IsAuthenticated]
    renderer_classes = [SSERenderer]

    def post(self, request):
        session_id = request.data['session_id']
        message = request.data['message'].strip()
        if not message:
            return Response({
                'result': '消息不能为空'
            })
        try:
            session = Session.objects.get(pk=session_id, friend__me__user=request.user)
        except Session.DoesNotExist:
            return Response({
                'result': '会话不存在'
            })
        friend = session.friend
        # 安全拦截：角色被删除后，已有 Session 只能查看历史，不能再发起新对话
        if not friend.character:
            return Response({
                'result': '该角色已被删除，无法继续对话'
            })
        app = ChatGraph.create_app()

        inputs: AgentState = {
            'messages': [HumanMessage(content=message)]
        }
        inputs = add_system_prompt(inputs, friend)
        inputs = add_recent_messages(inputs, session)
        # 非流式回复
        # res = app.invoke(inputs)
        

        response = StreamingHttpResponse(self.event_stream(app, inputs, friend, session, message), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        # 避免让nginx缓存
        response['X-Accel-Buffering'] = 'no'
        return response
    
    async def tts_sender(self, app, inputs, mq, ws, task_id):
        # stream()同步生成器
        # astream()异步生成器
        async for msg, metadata in app.astream(inputs, stream_mode="messages"):
            if isinstance(msg, BaseMessageChunk):
                if msg.content:
                    # 发送用户消息给阿里云百炼TTS大模型
                    await ws.send(json.dumps({
                        "header": {
                            "action": "continue-task",
                            "task_id": task_id, # 随机uuid
                            "streaming": "duplex"
                        },
                        "payload": {
                            "input": {
                                "text": msg.content
                            }
                        }
                    }))
                    # put()：生产者可以等待，不着急的场景
                    # put_nowait()：需要立即知道是否成功，或者不想阻塞的场景（比如配合 try/except 做降级处理）
                    mq.put_nowait({
                        'content': msg.content
                    })
                if isinstance(msg, AIMessageChunk) and hasattr(msg, 'usage_metadata') and msg.usage_metadata:
                    mq.put_nowait({
                        'usage': msg.usage_metadata
                    })
        await ws.send(json.dumps({
            "header": {
                "action": "finish-task",
                "task_id": task_id,
                "streaming": "duplex"
            },
            "payload": {
                "input": {} # input不能省去，否则会报错
            }
        }))

    async def tts_receiver(self, mq, ws):
        async for msg in ws:
            if isinstance(msg, bytes):
                audio = base64.b64encode(msg).decode('utf-8')
                # 收到阿里云百炼TTS大模型返回的用户消息音频
                mq.put_nowait({'audio': audio})
            else:
                data = json.loads(msg)
                event = data['header']['event']
                if event in ['task-finished', 'task-failed']:
                    break

    # 语音合成
    # 阿里云TTS文档：https://bailian.console.aliyun.com/cn-beijing/?spm=5176.12818093_47.console-base_product-drawer-right.dproducts-and-services-sfm.258b16d0dZyCzu&tab=api#/api/?type=model&url=2853143
    async def run_tts_tasks(self, app, inputs, mq):
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
                    "task_id": task_id, # 随机uuid
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
                        "format": "mp3",		        # 音频格式
                        "sample_rate": 22050,	        # 采样率
                        "volume": 50,			        # 音量
                        "rate": 1.25,				    # 语速
                        "pitch": 1				        # 音调
                    },
                    "input": {# input不能省去，不然会报错
                    }
                }
            }))
            async for msg in ws:
                if json.loads(msg)['header']['event'] == 'task-started':
                    break
            await asyncio.gather(
                self.tts_sender(app, inputs, mq, ws, task_id),
                self.tts_receiver(mq, ws),
            )


    def work(self, app, inputs, mq):
        try:
            asyncio.run(self.run_tts_tasks(app, inputs, mq))
        finally:
            mq.put_nowait(None)

    def event_stream(self, app, inputs, friend, session, message) -> Generator[bytes, Any, None]:
        # 线程安全的队列
        mq = Queue()
        # 创建线程
        # 主线程是下面的while循环负责将队列的消息进行逐个消费
        thread = threading.Thread(target=self.work, args=(app, inputs, mq))
        thread.start()

        full_output = ''
        full_usage = {}
        while True:
            msg = mq.get()
            if not msg:
                break
            # 若是用户消息，则流式返回用户消息
            if msg.get('content', None):
                full_output += msg['content']
                yield f'data: {json.dumps({"content": msg["content"]}, ensure_ascii=False)}\n\n'.encode('utf-8')
            # 若是用户消息音频，则流式返回用户消息音频
            if msg.get('audio', None):
                yield f'data: {json.dumps({"audio": msg["audio"]}, ensure_ascii=False)}\n\n'.encode('utf-8')
            if msg.get('usage', None):
                full_usage = msg['usage']
        yield 'data: [DONE]\n\n'.encode('utf-8')
        input_tokens = full_usage.get('input_tokens', 0)
        output_tokens = full_usage.get('output_tokens', 0)
        total_tokens = full_usage.get('total_tokens', 0)
        Message.objects.create(
            session = session,
            user_message = message[:500],
            input = json.dumps(
                [m.model_dump() for m in inputs['messages']],
                ensure_ascii=False
            )[:10000],
            output = full_output[:500],
            input_tokens = input_tokens,
            output_tokens = output_tokens,
            total_tokens = total_tokens
        )
        friend.update_time = now()
        friend.save()
        session.update_time = now()
        session.save()
        if Message.objects.filter(session=session).count() % 10 == 0:
            update_memory(friend, session)