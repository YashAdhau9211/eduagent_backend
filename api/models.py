# api/models.py
import uuid
from django.db import models

class ChatSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, default="New Chat")
    # user = models.ForeignKey(User, on_delete=models.CASCADE) # Link to user model later
    subject = models.CharField(max_length=100, blank=True, null=True) # Store associated subject
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.id})"

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    chat_session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    # Optional: Store individual answers if needed for history review
    # rag_answer = models.TextField(blank=True, null=True)
    # llm_answer = models.TextField(blank=True, null=True)
    # web_answer = models.TextField(blank=True, null=True)
    # sources = models.JSONField(blank=True, null=True) # Store web source URLs

    class Meta:
        ordering = ['timestamp'] # Ensure messages are ordered correctly

    def __str__(self):
        return f"{self.role} message in chat {self.chat_session.id} at {self.timestamp}"