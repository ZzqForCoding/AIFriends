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

    2026-04 核心入口，负责三件事：
        1. 确保当前用户与指定角色之间存在 Friend 记录；若不存在则创建，并立即把
           Character 的快照信息（名称、头像、背景图、简介、开场白、作者信息）写入 Friend，
           防止 Character 被删除后前端无法展示历史记录（SET_NULL 保护）。
        2. 懒创建会话逻辑：
           - 若该 Friend 下已有 Session，返回最新的一个作为 current_session_id，
             让用户进入"继续聊"状态；
           - 若没有任何 Session，返回 current_session_id=None，前端进入"虚拟新对话"状态，
             等用户发送第一条消息时再由前端调用 /api/friend/session/create/ 真正创建 Session。
        3. 组装返回数据：快照字段优先，若 Character 仍存在则回退到实时对象。
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            character_id = request.data['character_id']
            user = request.user
            user_profile = UserProfile.objects.get(user=user)

            # 1. 确保 Friend 存在。如果新建，则写入默认值占位，防止后续 .save() 异常
            friend, created = Friend.objects.get_or_create(
                character_id=character_id,
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
                character = Character.objects.get(pk=character_id)
                friend.character_name = character.name
                friend.character_photo.name = character.photo.name if character.photo else ''
                friend.character_background_image.name = character.background_image.name if character.background_image else ''
                friend.character_profile = character.profile
                friend.character_opening_message = character.opening_message
                friend.author_id = character.author.id if character.author else None
                friend.author_username = character.author.user.username if character.author else ''
                friend.author_photo.name = character.author.photo.name if character.author and character.author.photo else ''
                friend.save()

            # 2. 懒创建会话：取最新一个 Session，若没有则返回 None
            current_session = friend.sessions.first()

            # 3. 组装 Session 列表（只返回前 N 个，N 由 settings.SESSION_PAGE_COUNT 控制）
            sessions_raw = friend.sessions.all()[:settings.SESSION_PAGE_COUNT]
            sessions = []
            for s in sessions_raw:
                sessions.append({
                    'id': s.id,
                    'session_name': s.session_name,
                    'create_time': s.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                })

            # 4. 组装角色信息：快照字段优先，回退到实时对象
            character = friend.character  # 角色被删除后这里为 None
            author = character.author if character else None

            return Response({
                'result': 'success',
                'friend': {
                    'id': friend.id,  # 始终返回 friend.id，即使 character 已被删除
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
                'sessions': sessions,
                'current_session_id': current_session.id if current_session else None
            })
        except:
            return Response({
                'result': '系统异常，请稍后重试'
            })
