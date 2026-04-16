from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from web.models.friend import Message


class GetHistoryView(APIView):
    """
    GET_HISTORY /api/friend/message/get_history/

    2026-04 大改说明：
        - Message 模型已移除 friend 外键，改为直接按 session_id 查询。
        - 通过 session__friend__me__user=request.user 做权限校验，
          确保用户只能访问自己的会话消息。
        - 分页方式：last_message_id（0 表示首次加载），每次返回按 id 倒序的 10 条消息。
          前端拿到消息后按原顺序 reverse prepend 到列表顶部。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            # 默认值 0 表示第一次加载，不需要过滤 pk__lt
            last_message_id = int(request.query_params.get('last_message_id', 0))
            session_id = request.query_params.get('session_id')

            queryset = Message.objects.filter(
                session_id=session_id,
                session__friend__me__user=request.user
            )
            if last_message_id > 0:
                queryset = queryset.filter(pk__lt=last_message_id)

            messages_raw = queryset.order_by('-id')[:10]
            messages = []
            for m in messages_raw:
                messages.append({
                    'id': m.id,
                    'user_message': m.user_message,
                    'output': m.output
                })

            return Response({
                'result': 'success',
                'messages': messages
            })
        except:
            return Response({
                'result: ': '系统异常，请稍后重试'
            })
