from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from web.models.character import Character
from web.models.friend import Friend
from web.views.utils.photo import remove_old_photo


class RemoveFriendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            friend_id = request.data['friend_id']
            friend = Friend.objects.get(id=friend_id, me__user=request.user)

            # 安全删除快照图片：若仍有其他 Friend 或 Character 引用该文件，则保留物理文件
            photo_referenced = Friend.objects.filter(
                character_photo__contains=friend.character_photo.name
            ).exclude(id=friend.id).exists() if friend.character_photo else False
            if not photo_referenced:
                character_photo_referenced = Character.objects.filter(
                    photo__contains=friend.character_photo.name
                ).exists() if friend.character_photo else False
                if not character_photo_referenced:
                    remove_old_photo(friend.character_photo)

            bg_referenced = Friend.objects.filter(
                character_background_image__contains=friend.character_background_image.name
            ).exclude(id=friend.id).exists() if friend.character_background_image else False
            if not bg_referenced:
                character_bg_referenced = Character.objects.filter(
                    background_image__contains=friend.character_background_image.name
                ).exists() if friend.character_background_image else False
                if not character_bg_referenced:
                    remove_old_photo(friend.character_background_image)

            author_photo_referenced = Friend.objects.filter(
                author_photo__contains=friend.author_photo.name
            ).exclude(id=friend.id).exists() if friend.author_photo else False
            if not author_photo_referenced:
                remove_old_photo(friend.author_photo)

            friend.delete()
            return Response({
                'result': 'success'
            })
        except:
            return Response({
                'result': '系统异常，请稍后重试'
            })
