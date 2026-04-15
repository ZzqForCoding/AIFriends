from django.contrib import admin

from web.models.character import Character
from web.models.friend import Friend, Session, Message, SystemPrompt
from web.models.user import UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)   # 不能把逗号删除

@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    # 外键加进来，使在管理员后台的新建和修改中，这个字段的填值方式从下拉框变成打开另一个页面进行选择(自动分页)，从而避免卡死
    raw_id_fields = ('author',)

@admin.register(Friend)
class FriendAdmin(admin.ModelAdmin):
    raw_id_fields = ('me', 'character', )

@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    raw_id_fields = ('friend', )

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    raw_id_fields = ('session', )

admin.site.register(SystemPrompt)