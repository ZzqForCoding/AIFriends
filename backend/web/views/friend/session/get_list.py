from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.friend import Session


class GetListView(APIView):
    """
    GET_LIST /api/friend/session/get_list/

    2026-04 新增接口：为侧边栏提供某 Friend 下的 Session 分页列表。

    分页说明：
        - items_count 表示"已经加载了多少条"，由前端传入，用于 offset 分页。
        - last_session_id 用于基于主键的"加载更多"兜底（当数据更新频繁时更稳定）。
        - 排序规则：按 update_time 倒序、id 倒序，最新的会话排在最前面。
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            friend_id = int(request.query_params.get('friend_id', 0))
            last_session_id = int(request.query_params.get('last_session_id', 0))
            # 注意：默认值必须是 0，不能是 settings.SESSION_PAGE_COUNT，
            # 否则第一次请求就会跳过前 N 条记录
            items_count = int(request.query_params.get('items_count', 0))

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
