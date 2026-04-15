from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.friend import Session

class GetListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            friend_id = int(request.query_params.get('friend_id', 0))
            last_session_id = int(request.query_params.get('last_session_id', 0))
            items_count = int(request.query_params.get('items_count', settings.SESSION_PAGE_COUNT))
            queryset = Session.objects.filter(
                friend_id=friend_id,
                friend__me__user=request.user
            ).order_by('-update_time', '-id')
            if last_session_id > 0:
                queryset = queryset.filter(pk__lt=last_session_id)
            sessions_raw = queryset[items_count: items_count + settings.SESSION_PAGE_COUNT]
            sessions = []
            for s in sessions_raw:
                sessions.append({
                    'id': s.id,
                    'session_name': s.session_name,
                    'create_time': s.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                })
            return Response({
                'result': 'success',
                'sessions': sessions
            })
        except:
            return Response({
                'result': '系统异常，请稍后重试'
            })    
            

