from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.friend import Friend

class GetListFriendView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            items_count = int(request.query_params.get('items_count', 0))
            friends_raw = Friend.objects.filter(
                me__user=request.user
            ).order_by('-update_time')[items_count: items_count + 20]
            friends = []
            # Character 被删除后 friend.character 为 None，所有字段必须做空保护，
            # 优先使用 Friend 上的快照字段保证展示不中断。
            for friend in friends_raw:
                character = friend.character
                author = character.author if character else None
                friends.append({
                    'id': friend.id,
                    'character': {
                        'id': character.id if character else None,
                        'name': friend.character_name or (character.name if character else '未知角色'),
                        'profile': friend.character_profile or (character.profile if character else ''),
                        'photo': friend.character_photo.url if friend.character_photo else (character.photo.url if character and character.photo else ''),
                        'background_image': friend.character_background_image.url if friend.character_background_image else (character.background_image.url if character and character.background_image else ''),
                        'author': {
                            'user_id': friend.author_id or (author.id if author else None),
                            'username': friend.author_username or (author.user.username if author else ''),
                            'photo': friend.author_photo.url if friend.author_photo else (author.photo.url if author and author.photo else '')
                        } if (friend.author_id or author) else None
                    }
                })
            return Response({
                'result': 'success',
                'friends': friends
            })
        except:
            return Response({
                'result': '系统异常，请稍后重试'
            })