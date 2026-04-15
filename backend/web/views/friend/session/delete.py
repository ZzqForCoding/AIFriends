from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.friend import Session

class DeleteView(APIView):
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