from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from web.models.friend import Message

# 获取指定 Session 的消息历史（滚动加载）
# 从 Message 直接按 session_id 查询，不再依赖 friend_id
class GetHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        try:
            last_message_id = int(request.query_params.get('last_message_id'))
            session_id = request.query_params.get('session_id')
            # 通过 session__friend__me__user 校验用户是否有权访问该会话
            queryset = Message.objects.filter(session_id=session_id, session__friend__me__user=request.user)
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