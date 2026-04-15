from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.character import Character
from web.models.friend import Friend, Message, Session
from web.models.user import UserProfile

class GetOrCreateFriendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            character_id = request.data['character_id']
            user = request.user
            user_profile = UserProfile.objects.get(user=user)

            # 1. 确保 Friend 存在。如果新建，则把 Character 的快照信息写入 Friend，
            #    防止 Character 被删除后前端无法展示历史记录。
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

            # 如果是新建的 Friend，立即写入角色快照（Character 删除后仍可用）
            if created:
                character = Character.objects.get(pk=character_id)
                friend.character_name = character.name
                friend.character_photo = character.photo.url if character.photo else ''
                friend.character_background_image = character.background_image.url if character.background_image else ''
                friend.character_profile = character.profile
                friend.character_opening_message = character.opening_message
                friend.author_id = character.author.id if character.author else None
                friend.author_username = character.author.user.username if character.author else ''
                friend.author_photo = character.author.photo.url if character.author and character.author.photo else ''
                friend.save()

            # 2. 懒创建会话逻辑：
            #    - 如果该 Friend 下已有 Session，直接返回最新的一个，让用户接着聊
            #    - 如果没有 Session，返回 current_session_id=None，前端进入"虚拟新对话"状态
            current_session = friend.sessions.first()
            
            # 3. 组装已有的 Session 列表
            sessions_raw = friend.sessions.all()[:settings.SESSION_PAGE_COUNT]
            sessions = []
            for s in sessions_raw:
                sessions.append({
                    'id': s.id,
                    'session_name': s.session_name,
                    'create_time': s.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                })

                
            # 3. 组装角色信息：快照字段优先，若 Character 仍存在则回退到实时对象
            character = friend.character  # 角色被删除后这里为 None
            author = character.author if character else None
            
            return Response({
                'result': 'success',
                'friend': {
                    'id': friend.id if character else None,
                    'character_opening_message': friend.character_opening_message,
                    'character': {
                        'id': character.id if character else None,
                        'name': friend.character_name or (character.name if character else '未知角色'),
                        'profile': friend.character_profile or (character.profile if character else ''),
                        'photo': friend.character_photo or (character.photo.url if character and character.photo else ''),
                        'background_image': friend.character_background_image or (character.background_image.url if character and character.background_image else ''),
                        'author': {
                            'id': friend.author_id or (author.id if author else None),
                            'username': friend.author_username or (author.user.username if author else ''),
                            'photo': friend.author_photo or (author.photo.url if author and author.photo else '')
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