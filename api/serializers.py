from rest_framework import serializers
from .models import ChatSession, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'timestamp']

class ChatSessionSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = ChatSession
        fields = ['id', 'name', 'subject', 'created_at', 'owner_username']
        read_only_fields = ['created_at'] # Keep existing read_only if needed

class ChatSessionDetailSerializer(ChatSessionSerializer): # <<< AUTH: Inherit from updated ChatSessionSerializer
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta(ChatSessionSerializer.Meta): # <<< AUTH: Inherit Meta from the parent
        fields = ChatSessionSerializer.Meta.fields + ['messages']


class QueryRequestSerializer(serializers.Serializer):
    question = serializers.CharField(required=True)
    subject = serializers.CharField(required=True) # Keep subject if needed for context
    chat_id = serializers.UUIDField(required=True) # Used by view to find the session


class QueryResponseSerializer(serializers.Serializer):
    final = serializers.CharField()
    rag = serializers.CharField()
    llm = serializers.CharField()
    web = serializers.CharField()
    sources = serializers.ListField(child=serializers.CharField())