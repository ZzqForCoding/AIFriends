from django.db import models
from django.utils.timezone import now, localtime

from web.models.character import Character, photo_upload_to, background_image_upload_to
from web.models.user import UserProfile, photo_upload_to as user_photo_upload_to


class Friend(models.Model):
    """
    Friend: 用户与角色之间的关系记录

    2026-04 大改说明：
        1. 引入 SET_NULL：角色（Character）被删除后，Friend 和历史记录仍然保留，
           仅 character 外键变为 null，保证用户能继续查看旧聊天记录。
        2. 新增快照字段（character_name / character_photo / character_profile 等）：
           当 Character 被删除后，前端仍能从 Friend 中读取角色的基本信息和图片 URL，
           避免历史页面和聊天弹窗出现 404 或空白。
        3. 新增作者快照字段（author_id / author_username / author_photo）：
           同样用于角色删除后的信息保护。
    """
    me = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    character = models.ForeignKey(
        Character,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='friends'
    )
    # 角色快照字段：Character 删除后仍可展示
    character_name = models.CharField(max_length=50, blank=True, default='')
    character_photo = models.ImageField(upload_to=photo_upload_to, max_length=500, blank=True, default='')
    character_background_image = models.ImageField(upload_to=background_image_upload_to, max_length=500, blank=True, default='')
    character_profile = models.TextField(default='', blank=True)
    character_opening_message = models.TextField(default='', blank=True)
    # 作者快照字段
    author_id = models.IntegerField(null=True, blank=True)
    author_username = models.CharField(max_length=50, blank=True, default='')
    author_photo = models.ImageField(upload_to=user_photo_upload_to, max_length=500, blank=True, default='')

    memory = models.TextField(default="", max_length=5000, blank=True, null=True)
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)

    class Meta:
        ordering = ['-update_time']

    def __str__(self):
        name = self.character_name or (self.character.name if self.character else '未知角色')
        return f"{name} - {self.me.user.username} - {localtime(self.create_time).strftime('%Y-%m-%d %H:%M:%S')}"


class Session(models.Model):
    """
    Session: 一个 Friend 下可以有多个会话，实现多会话历史管理

    2026-04 新增模型，配合"懒创建会话"架构：
        - 用户首次打开聊天页时，若该 Friend 下无 Session，前端进入"虚拟新对话"状态。
        - 用户发送第一条消息时（或手动点击 + 时），才真正创建 Session 记录。
        - Message 不再直接外键到 Friend，而是外键到 Session。
    """
    friend = models.ForeignKey(Friend, on_delete=models.CASCADE, related_name='sessions')
    session_name = models.CharField(max_length=100, default="新的对话")
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)

    class Meta:
        ordering = ['-update_time']

    def __str__(self):
        return f"{self.session_name} - {self.friend.character_name or (self.friend.character.name if self.friend.character else '未知角色')} - {localtime(self.create_time).strftime('%Y-%m-%d %H:%M:%S')}"


class Message(models.Model):
    """
    Message: 聊天消息

    2026-04 大改说明：
        1. 移除旧的 friend 外键，改为外键到 Session，实现"多会话隔离"。
        2. 开场白消息以 user_message=''、output='开场白内容' 的形式存储，
           这样 get_history 加载时能保持完整上下文。
        3. ordering = ['-id']：按主键倒序，配合 last_message_id 实现向上滚动分页。
    """
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
    """
    SystemPrompt: 系统提示词模板

    当前主要用于 AI 回复的身份定位、性格约束、长期记忆拼接。
    由 add_system_prompt() 在聊天时动态读取并按顺序拼接。
    """
    title = models.CharField(max_length=100)
    order_number = models.IntegerField(default=0)
    prompt = models.TextField(max_length=10000)
    create_time = models.DateTimeField(default=now)
    update_time = models.DateTimeField(default=now)

    def __str__(self):
        return f"{self.title} - {self.order_number} - {self.prompt[:50]} - {localtime(self.create_time).strftime('%Y-%m-%D %H:%M:%S')}"
