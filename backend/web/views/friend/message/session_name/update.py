
import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import SecretStr

from web.models.friend import Session, SystemPrompt


def create_system_message():
    system_prompts = SystemPrompt.objects.filter(title='会话名称').order_by('order_number')
    prompt = ''
    for sp in system_prompts:
        prompt += sp.prompt
    return SystemMessage(prompt)

def create_human_message(user_message):
    prompt = f'【用户问题】\n{user_message}\n'
    return HumanMessage(prompt)

def update_session_name(session_id, user_message):
    """异步生成会话标题（仅当标题仍为默认值时更新）"""
    try:
        api_key = os.getenv('API_KEY')
        base_url = os.getenv('API_BASE')
        if not api_key or not base_url:
            return

        llm = ChatOpenAI(
            model='deepseek-v3.2',
            api_key=SecretStr(api_key),
            base_url=base_url,
            temperature=0.3,
            max_completion_tokens=20,
        )
        messages = [
            create_system_message(),
            create_human_message(user_message),
        ]
        response = llm.invoke(messages)
        name =  str(response.content or '').strip()
        if len(name) > 20:
            name = name[:20]
        if name:
            Session.objects.filter(
                id=session_id,
                session_name='新的对话'
            ).update(session_name=name)
    except Exception as e:
        print(f'generate session name failed: {e}')