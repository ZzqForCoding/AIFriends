import os

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import SecretStr
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.character import Character
from web.models.friend import SystemPrompt
from web.models.user import UserProfile


class CreateCharacterView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            user_profile = UserProfile.objects.get(user=user)
            name = request.data.get('name').strip()
            profile = request.data.get('profile').strip()[:100000]
            photo = request.FILES.get('photo', None)
            background_image = request.FILES.get('background_image', None)

            if not name:
                return Response({
                    'result': '名字不能为空'
                })
            if not profile:
                return Response({
                    'result': '角色介绍不能为空'
                })
            if not photo:
                return Response({
                    'result': '头像不能为空'
                })
            if not background_image:
                return Response({
                    'result': '聊天背景不能为空'
                })

            system_prompts = SystemPrompt.objects.filter(title='开场白').order_by('order_number')
            prompt = ''
            for sp in system_prompts:
                prompt += sp.prompt

            llm = ChatOpenAI(
                model='deepseek-v3.2',
                api_key=SecretStr(os.getenv('API_KEY') or ''),
                base_url=os.getenv('API_BASE')
            )

            messages = [
                SystemMessage(prompt),
                HumanMessage(f"角色名称：{name}\n角色人设：\n{profile}")
            ]

            try:
                res = llm.invoke(messages)
                token_usage = res.response_metadata.get('token_usage', {})
                opening_message = res.content
                opening_message_input_tokens = token_usage.get('prompt_tokens', 0)
                opening_message_output_tokens = token_usage.get('completion_tokens', 0)
                opening_message_total_tokens = token_usage.get('total_tokens', 0)
            except Exception as e:
                # LLM 失败时降级：用角色名做默认开场白z
                print(f'generate opening message failed: {e}')
                opening_message = f"你好，我是{name}，很高兴认识你。"
                opening_message_input_tokens = 0
                opening_message_output_tokens = 0
                opening_message_total_tokens = 0

            Character.objects.create(
                author=user_profile,
                name=name,
                profile=profile,
                opening_message=opening_message,
                opening_message_input_tokens=opening_message_input_tokens,
                opening_message_output_tokens=opening_message_output_tokens,
                opening_message_total_tokens=opening_message_total_tokens,
                photo=photo,
                background_image=background_image,
            )
            return Response({
                'result': 'success'
            })
        except:
            return Response({
                'result': '系统异常，请稍后重试'
            })