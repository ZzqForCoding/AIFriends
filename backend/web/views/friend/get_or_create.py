from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from web.models.friend import Friend, Message
from web.models.user import UserProfile

class GetOrCreateFriendView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            character_id = request.data['character_id']
            user = request.user
            user_profile = UserProfile.objects.get(user=user)

            friend, created = Friend.objects.get_or_create(
                character_id=character_id,
                me=user_profile
            )
            character = friend.character
            if created and character.opening_message:
                Message.objects.create(
                    friend=friend,
                    user_message='',
                    input='',
                    output=character.opening_message,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0
                )
            author = character.author
            return Response({
                'result': 'success',
                'friend': {
                    'id': friend.id,
                    'character': {
                        'id': character.id,
                        'name': character.name,
                        'profile': character.profile,
                        'photo': character.photo.url,
                        'background_image': character.background_image.url,
                        'author': {
                            'id': author.id,
                            'username': author.user.username,
                            'photo': author.photo.url
                        }
                    }
                }
            })
        except:
            return Response({
                'result': '系统异常，请稍后重试'
            })