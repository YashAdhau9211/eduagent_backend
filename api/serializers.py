# api/serializers.py
from rest_framework import serializers
from .models import ChatSession, ChatMessage

# --- Model Serializers ---
class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'timestamp'] # Exclude chat_session for nesting

class ChatSessionSerializer(serializers.ModelSerializer):
    # Optionally nest messages, but can be heavy. Better to have separate endpoint.
    # messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = ['id', 'name', 'subject', 'created_at']

class ChatSessionDetailSerializer(serializers.ModelSerializer):
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta:
        model = ChatSession
        fields = ['id', 'name', 'subject', 'created_at', 'messages']


# --- Request Data Serializers ---
class QueryRequestSerializer(serializers.Serializer):
    question = serializers.CharField(required=True)
    subject = serializers.CharField(required=True)
    chat_id = serializers.UUIDField(required=True) # Need chat ID to save history


# --- Response Data Serializers ---
class QueryResponseSerializer(serializers.Serializer):
    final = serializers.CharField()
    rag = serializers.CharField()
    llm = serializers.CharField()
    web = serializers.CharField()
    sources = serializers.ListField(child=serializers.CharField())