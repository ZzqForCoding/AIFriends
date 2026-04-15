from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from web.models.character import Character
from web.models.friend import Friend
from web.views.utils.photo import remove_old_photo


class RemoveCharacterView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            character_id = request.data['character_id']
            character = Character.objects.get(id=character_id, author__user=request.user)

            # 安全删除角色图片：若仍有 Friend 的快照字段引用该文件，则保留物理文件，
            # 避免 Character 删除后历史记录中的图片全部 404。
            photo_referenced = Friend.objects.filter(
                character_photo__contains=character.photo.name
            ).exists() if character.photo else False
            if not photo_referenced:
                remove_old_photo(character.photo)

            bg_referenced = Friend.objects.filter(
                character_background_image__contains=character.background_image.name
            ).exists() if character.background_image else False
            if not bg_referenced:
                remove_old_photo(character.background_image)

            character.delete()
            return Response({
                'result': 'success',
            })
        except:
            return Response({
                'result': '系统异常，请稍后重试'
            })