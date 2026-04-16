from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.friend import Friend, Message, Session


class CreateView(APIView):
    """
    CREATE /api/friend/session/create/

    2026-04 新增接口，配合"懒创建会话"架构：
        - 前端在两种场景下调用：
          a) 虚拟新对话状态下用户发送了第一条消息；
          b) 用户手动点击侧边栏的"+"新建会话按钮。
        - 后端为指定 Friend 创建一个新的真实 Session，
          并自动在该 Session 中插入一条开场白消息（user_message=''）。
          这样 ChatHistory 从后端加载历史时就能拿到完整的开场白上下文，
          保证虚拟状态和真实状态的一致性。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            friend_id = int(request.data.get('friend_id', 0))
            friend = Friend.objects.get(pk=friend_id, me__user=request.user)

            # 创建新的真实 Session
            session = Session.objects.create(friend=friend)

            # 若角色有开场白，自动插入到该 Session 的第一条消息中
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
