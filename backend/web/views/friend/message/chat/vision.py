import os
from typing import List, Optional

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


def describe_images(image_bases: List[str], user_prompt: str = "") -> Optional[str]:
    """
    调用视觉模型（qwen-vl-max）对多张图片进行描述。
    返回所有图片的文字描述，失败时返回 None。
    """
    if not image_bases:
        return None

    api_key = os.getenv('API_KEY')
    base_url = os.getenv('API_BASE')
    if not api_key or not base_url:
        return None

    llm = ChatOpenAI(
        model='qwen-vl-max',
        api_key=SecretStr(api_key),
        base_url=base_url,
        max_tokens=1024,
    )

    prompt_text = user_prompt or '请详细描述这张图片的内容，包括场景、人物、物体、文字等所有可见信息。'

    content_parts: list = [{'type': 'text', 'text': prompt_text}]
    for img in image_bases:
        content_parts.append({
            'type': 'image_url',
            'image_url': {'url': f'data:image/png;base64,{img}'},
        })

    msg = HumanMessage(content=content_parts)

    try:
        res = llm.invoke([msg])
        return res.content if isinstance(res.content, str) else str(res.content)
    except Exception:
        return None
