from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.character import Character
from web.models.friend import Friend, Message, Session
from web.models.user import UserProfile


class GetOrCreateFriendView(APIView):
    """
    GET_OR_CREATE /api/friend/get_or_create/

    2026-04 核心入口，支持两种调用方式：
        1. 传 friend_id：从我的好友列表进入，直接返回已有 Friend（角色已删也能查看快照）。
        2. 传 character_id：从角色广场进入，校验角色存在后查找/创建 Friend 并写入快照。

    懒创建会话逻辑：
       - 若该 Friend 下已有 Session，返回最新的一个作为 current_session_id；
       - 若没有任何 Session，返回 current_session_id=None，前端进入"虚拟新对话"状态。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            friend_id = request.data.get('friend_id')
            character_id = request.data.get('character_id')
            user = request.user
            user_profile = UserProfile.objects.get(user=user)

            # ========== 入口 1：从我的好友列表进入 ==========
            if friend_id:
                try:
                    friend = Friend.objects.get(pk=friend_id, me=user_profile)
                except Friend.DoesNotExist:
                    return Response({'result': '好友不存在'}, status=404)

            # ========== 入口 2：从角色广场进入 ==========
            elif character_id:
                # 校验角色是否还存在（被删了就拒绝创建）
                try:
                    character = Character.objects.get(pk=character_id)
                except Character.DoesNotExist:
                    return Response({'result': '该角色已被删除'}, status=404)

                # 查找或创建 Friend
                friend, created = Friend.objects.get_or_create(
                    character=character,
                    me=user_profile,
                    defaults={
                        'character_name': '',
                        'character_photo': '',
                        'character_background_image': '',
                        'character_profile': '',
                        'character_opening_message': '',
                        'author_id': None,
                        'author_username': '',
                        'author_photo': '',
                    }
                )

                # 若是新建的 Friend，立即写入角色快照（Character 删除后仍可用）
                if created:
                    friend.character_name = character.name
                    friend.character_photo.name = character.photo.name if character.photo else ''
                    friend.character_background_image.name = character.background_image.name if character.background_image else ''
                    friend.character_profile = character.profile
                    friend.character_opening_message = character.opening_message
                    friend.author_id = character.author.id if character.author else None
                    friend.author_username = character.author.user.username if character.author else ''
                    friend.author_photo.name = character.author.photo.name if character.author and character.author.photo else ''
                    friend.save()

            else:
                return Response({'result': 'friend_id 或 character_id 至少传一个'}, status=400)

            # ========== 统一组装返回数据（快照字段优先） ==========
            current_session = friend.sessions.first()
            character = friend.character  # 角色被删除后这里为 None
            author = character.author if character else None

            return Response({
                'result': 'success',
                'friend': {
                    'id': friend.id,
                    'character_opening_message': friend.character_opening_message,
                    'character': {
                        'id': character.id if character else None,
                        'name': friend.character_name or (character.name if character else '未知角色'),
                        'profile': friend.character_profile or (character.profile if character else ''),
                        'photo': friend.character_photo.url if friend.character_photo else (character.photo.url if character and character.photo else ''),
                        'background_image': friend.character_background_image.url if friend.character_background_image else (character.background_image.url if character and character.background_image else ''),
                        'author': {
                            'id': friend.author_id or (author.id if author else None),
                            'username': friend.author_username or (author.user.username if author else ''),
                            'photo': friend.author_photo.url if friend.author_photo else (author.photo.url if author and author.photo else '')
                        } if (friend.author_id or author) else None
                    }
                },
                'current_session_id': current_session.id if current_session else None
            })
        except:
            import traceback
            traceback.print_exc()
            return Response({
                'result': '系统异常，请稍后重试'
            })
