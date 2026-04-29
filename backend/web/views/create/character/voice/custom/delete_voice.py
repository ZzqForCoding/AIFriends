import os

import requests


def delete_voice(voice_id):
    headers = {
        "Authorization": f"Bearer {os.getenv('API_KEY')}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "voice-enrollment",
        "input": {
            "action": "delete_voice",
            "voice_id": voice_id
        }
    }
    voice_url = os.getenv('VOICE_URL')
    if voice_url is None:
        raise ValueError("环境变量 VOICE_URL 未设置")
    response = requests.post(voice_url, headers=headers, json=data)
    return response.json()