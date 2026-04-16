from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.friend import Session


class DeleteView(APIView):
    """
    DELETE /api/friend/session/delete/

    2026-04 新增接口：删除指定 Session 及其关联的所有 Message（级联删除）。

    安全校验：
        - 通过 friend__me__user=request.user 确保用户只能删除自己的会话。
        - 使用 filter + exists + delete 的标准写法，防止 DoesNotExist 异常。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            session_id = request.data['session_id']
            sessions = Session.objects.filter(pk=session_id, friend__me__user=request.user)
            if sessions.exists():
                sessions.delete()
            return Response({
                'result': 'success'
            })
        except:
            return Response({
                'result': '系统异常，请稍后重试'
            })
