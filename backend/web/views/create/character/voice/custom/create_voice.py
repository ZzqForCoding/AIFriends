import os

import requests


def create_voice(voice_url, prefix):
    headers = {
        "Authorization": f"Bearer {os.getenv('API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "voice-enrollment",
        "input": {
            "action": "create_voice",
            "target_model": "cosyvoice-v3-flash",
            "prefix": prefix,
            "url": voice_url
        }
    }
    voice_url = os.getenv('VOICE_URL')
    if voice_url is None:
        raise ValueError("环境变量 VOICE_URL 未设置")
    response = requests.post(voice_url, headers=headers, json=data)
    return response.json()