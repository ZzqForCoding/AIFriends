from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class LogoutView(APIView):
    permission_classes = [IsAuthenticated] # 强制用户必须登录
    def post(self, request):
        response = Response({
            'result': 'success',
        })
        response.delete_cookie('refresh_token')
        return response
