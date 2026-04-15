
from django.utils.timezone import now

from web.models.friend import Message, SystemPrompt
from web.views.friend.message.memory.graph import MemoryGraph
from langchain_core.messages import SystemMessage, HumanMessage

def create_system_message():
    system_prompts = SystemPrompt.objects.filter(title='记忆').order_by('order_number')
    prompt = ''
    for sp in system_prompts:
        prompt += sp.prompt
    return SystemMessage(prompt)
    

# 记忆总结：读取某个 Session 的最新 10 条消息，用 LLM 生成摘要后写回 Friend.memory
# 注意：长期记忆属于 Friend 级别（跨 Session），但生成时只取当前 Session 的最近对话
def create_human_message(friend, session):
    prompt = f'【原始记忆】\n{friend.memory}\n'
    prompt += f'【最近对话】\n'
    messages = list(Message.objects.filter(session=session).order_by('-id')[:10])
    messages.reverse()
    for m in messages:
        prompt += f'user: {m.user_message}\n'
        prompt += f'ai: {m.output}\n'
    return HumanMessage(prompt)


def update_memory(friend, session):
    app = MemoryGraph.create_app()

    inputs = {
        'messages': [
            create_system_message(),
            create_human_message(friend, session)
        ]
    }

    res = app.invoke(inputs)
    friend.memory = res['messages'][-1].content

    friend.update_time = now()
    friend.save()