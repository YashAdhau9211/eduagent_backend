import uuid
from django.db import models
from django.conf import settings

class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, default="New Chat")
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, # <<< AUTH: If user is deleted, delete their sessions
        related_name='chat_sessions' # <<< AUTH: How to access sessions from a user instance (user.chat_sessions.all())
    )
    subject = models.CharField(max_length=100, blank=True, null=True) # Store associated subject
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        owner_username = self.owner.username if self.owner else "Unassigned"
        return f"{self.name} by {owner_username} ({self.id})"

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    chat_session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)    # web_answer = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['timestamp'] # Ensure messages are ordered correctly

    def __str__(self):
        return f"{self.role} message in chat {self.chat_session.id} at {self.timestamp}"