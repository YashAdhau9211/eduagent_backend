# api/serializers.py
from rest_framework import serializers
from .models import ChatSession, ChatMessage


# --- Model Serializers ---
class ChatMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChatMessage
        # Exclude chat_session ID here as it's implied by the nesting context
        # or handled by the view if messages are retrieved directly.
        fields = ['id', 'role', 'content', 'timestamp']

class ChatSessionSerializer(serializers.ModelSerializer):
    # <<< AUTH: Add owner's username, make it read-only
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = ChatSession
        # <<< AUTH: Add 'owner_username' to fields for reading.
        # Exclude the actual 'owner' field ID from direct input/output here.
        # The owner is set in the view during creation.
        fields = ['id', 'name', 'subject', 'created_at', 'owner_username']
        # 'id' and 'created_at' are implicitly read-only or handled by Django.
        # 'owner_username' is explicitly read-only.
        # 'name' and 'subject' are writable (for creation/update).
        read_only_fields = ['created_at'] # Keep existing read_only if needed

class ChatSessionDetailSerializer(ChatSessionSerializer): # <<< AUTH: Inherit from updated ChatSessionSerializer
    messages = ChatMessageSerializer(many=True, read_only=True)

    class Meta(ChatSessionSerializer.Meta): # <<< AUTH: Inherit Meta from the parent
        # <<< AUTH: Add 'messages' to the inherited fields list
        fields = ChatSessionSerializer.Meta.fields + ['messages']
        # read_only_fields are inherited from parent Meta


# --- Request Data Serializers ---
class QueryRequestSerializer(serializers.Serializer):
    # No changes needed here regarding owner.
    # The view using this serializer MUST verify that the chat_id
    # belongs to the authenticated request.user.
    question = serializers.CharField(required=True)
    subject = serializers.CharField(required=True) # Keep subject if needed for context
    chat_id = serializers.UUIDField(required=True) # Used by view to find the session


# --- Response Data Serializers ---
class QueryResponseSerializer(serializers.Serializer):
    # No changes needed here regarding owner.
    final = serializers.CharField()
    rag = serializers.CharField()
    llm = serializers.CharField()
    web = serializers.CharField()
    sources = serializers.ListField(child=serializers.CharField())