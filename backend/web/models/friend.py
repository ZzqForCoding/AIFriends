from django.db import models
from django.utils.timezone import now, localtime

from web.models.character import Character
from web.models.user import UserProfile


class Friend(models.Model):
    me = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    # SET_NULL: 角色被删除后，Friend 和历史记录仍然保留，仅 character 外键变为 null
    character = models.ForeignKey(
        Character,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='friends'
    )
    # 角色快照字段：当 Character 被删除后，前端仍能从 Friend 中读取到角色的基本信息和图片 URL
    character_name = models.CharField(max_length=50, blank=True, default='')
    character_photo = models.CharField(max_length=500, blank=True, default='')
    character_background_image = models.CharField(max_length=500, blank=True, default='')
    character_profile = models.TextField(default='', blank=True)
    character_opening_message = models.TextField(default='', blank=True)
    # 作者快照字段：角色删除后仍能显示作者信息
    author_id = models.IntegerField(null=True, blank=True)
    author_username = models.CharField(max_length=50, blank=True, default='')
    author_photo = models.CharField(max_length=500, blank=True, default='')

    memory = models.TextField(default="", max_length=5000, blank=True, null=True)
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)

    class Meta:
        ordering = ['-update_time']

    def __str__(self):
        name = self.character_name or (self.character.name if self.character else '未知角色')
        return f"{name} - {self.me.user.username} - {localtime(self.create_time).strftime('%Y-%m-%d %H:%M:%S')}"


# Session: 一个 Friend 下可以有多个会话（Session），实现多会话历史管理
class Session(models.Model):
    friend = models.ForeignKey(Friend, on_delete=models.CASCADE, related_name='sessions')
    session_name = models.CharField(max_length=100, default="新的对话")
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)

    class Meta:
        ordering = ['-update_time']

    def __str__(self):
        return f"{self.session_name} - {self.friend.character_name or (self.friend.character.name if self.friend.character else '未知角色')} - {localtime(self.create_time).strftime('%Y-%m-%d %H:%M:%S')}"


class Message(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE, related_name='messages')
    user_message = models.TextField(max_length=500)
    input = models.TextField(max_length=10000)
    output = models.TextField(max_length=500)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    total_tokens = models.IntegerField(default=0)
    create_time = models.DateTimeField(default=now)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        friend = self.session.friend
        name = friend.character_name or (friend.character.name if friend.character else '未知角色')
        return f"{name} - {self.user_message[:50]} - {localtime(self.create_time).strftime('%Y-%m-%d %H:%M:%S')}"

class SystemPrompt(models.Model):
    title = models.CharField(max_length=100)
    order_number = models.IntegerField(default=0)
    prompt = models.TextField(max_length=10000)
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.title} - {self.order_number} - {self.prompt[:50]} - {localtime(self.create_time).strftime('%Y-%m-%D %H:%M:%S')}"
