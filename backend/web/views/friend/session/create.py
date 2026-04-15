from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.friend import Friend, Message, Session

class CreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            friend_id = int(request.data.get('friend_id', 0))

            friend = Friend.objects.get(pk=friend_id, me__user=request.user)

            # 为指定 Friend 创建一个新的真实 Session
            session = Session.objects.create(friend=friend)

            # 自动在该 Session 中插入开场白消息，保证 ChatHistory 从后端加载时能拿到完整上下文
            if friend.character_opening_message:
                Message.objects.create(
                    session=session,
                    user_message='',
                    input='',
                    output=friend.character_opening_message,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0
                )

            return Response({
                'result': 'success',
                'session': {
                    'id': session.id,
                    'session_name': session.session_name,
                    'create_time': session.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                }
            })
        except:
            return Response({
                'result': '系统异常，请稍后重试'
            })