# api/views.py
import asyncio
from rest_framework.views import APIView
from rest_framework import generics # <<< AUTH: Import generic views
from rest_framework.response import Response
from rest_framework import status, parsers
from rest_framework.permissions import IsAuthenticated, AllowAny # <<< AUTH: Import permissions
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.conf import settings
import tempfile
import os
import traceback
import shutil
from asgiref.sync import async_to_sync, sync_to_async

# Import your agent and models/serializers
from .agent import SubjectAgent
from .models import ChatSession, ChatMessage
from .serializers import (
    ChatSessionSerializer, ChatSessionDetailSerializer, ChatMessageSerializer,
    QueryRequestSerializer, QueryResponseSerializer
)

# --- Agent Instantiation ---
# (Keep your existing agent instantiation logic)
AGENTS = {
    subject: SubjectAgent(subject)
    for subject in ["Computer Science", "Math", "Physics"]
}
print("Initialized Agents:", list(AGENTS.keys()))

def _get_agent(subject):
    agent = AGENTS.get(subject)
    if not agent:
        raise Http404(f"Subject agent '{subject}' not found.")
    return agent

# --- Async DB Wrappers ---
@sync_to_async
def _save_message_async(chat_session, role, content):
    max_length = 10000
    truncated_content = content[:max_length] if content else ""
    if len(content) > max_length:
        print(f"Warning: Truncating assistant message for chat {chat_session.id}")
        truncated_content += " ... [truncated]"
    try:
        ChatMessage.objects.create(chat_session=chat_session, role=role, content=truncated_content)
    except Exception as db_e:
        print(f"Error saving message to DB for chat {chat_session.id}: {db_e}")
        traceback.print_exc()

# <<< AUTH: Update to include user check for ownership
@sync_to_async
def _get_chat_session_for_user_async(chat_id, user):
    """Gets a chat session only if it belongs to the specified user."""
    # Use get_object_or_404 with owner filter
    return get_object_or_404(ChatSession, pk=chat_id, owner=user)

# <<< AUTH: Remove unused async wrappers for ChatSession CRUD as generics handle them
# @_sync_to_async
# def _create_chat_session_async(name, subject, owner): ... # Replaced by perform_create
# @_sync_to_async
# def _get_all_chat_sessions_async(user): ... # Replaced by get_queryset
# @_sync_to_async
# def _update_chat_session_async(session, data): ... # Replaced by generic update
# @_sync_to_async
# def _delete_chat_session_async(session): ... # Replaced by generic delete


# --- API Views ---

class SubjectListView(APIView):
    """Lists available subjects (Public)."""
    # <<< AUTH: Explicitly allow anyone to access this view
    permission_classes = [AllowAny]

    def get(self, request, format=None):
        return Response(list(AGENTS.keys()), status=status.HTTP_200_OK)


class KnowledgeBaseView(APIView):
    """Handles knowledge base creation (file uploads) (Authenticated)."""
    parser_classes = [parsers.MultiPartParser]
    # <<< AUTH: Inherits IsAuthenticated permission from global settings

    # (Keep your existing _handle_kb_upload_async helper method - no auth changes needed inside it)
    async def _handle_kb_upload_async(self, agent, files):
        temp_dir = tempfile.mkdtemp()
        print(f"Created temporary directory for KB upload: {temp_dir}")
        saved_file_paths = []
        loop = asyncio.get_running_loop() # Get loop here
        try:
            for uploaded_file in files:
                if uploaded_file.size > getattr(settings, 'MAX_UPLOAD_SIZE_MB', 50) * 1024 * 1024:
                     raise ValueError(f"File '{uploaded_file.name}' exceeds size limit.")
                path = os.path.join(temp_dir, uploaded_file.name)
                print(f"Saving temporary file: {path}")
                with open(path, "wb") as f:
                    for chunk in uploaded_file.chunks():
                       await loop.run_in_executor(None, f.write, chunk)
                saved_file_paths.append(path)

            if not saved_file_paths:
                 raise ValueError("No valid files were processed for upload.")

            print(f"Calling create_knowledge_base for {agent.subject} with {len(saved_file_paths)} file paths.")
            await agent.create_knowledge_base(saved_file_paths)
            return {"message": f"Knowledge base update task completed for {agent.subject}"}
        except Exception as e:
             print(f"Error during async KB handling: {e}")
             traceback.print_exc()
             raise e
        finally:
             if os.path.exists(temp_dir):
                 try:
                    print(f"Cleaning up temporary directory: {temp_dir}")
                    await loop.run_in_executor(None, shutil.rmtree, temp_dir)
                 except Exception as cleanup_e:
                    print(f"Error cleaning up temporary directory {temp_dir}: {cleanup_e}")

    # Synchronous view method
    def post(self, request, subject, format=None):
        # <<< AUTH: request.user is available due to global IsAuthenticated permission
        try:
             agent = _get_agent(subject)
        except Http404 as e:
             return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        files = request.FILES.getlist('files')
        if not files:
            return Response({"error": "No files provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            result_data = async_to_sync(self._handle_kb_upload_async)(agent, files)
            return Response(result_data, status=status.HTTP_200_OK)
        except ValueError as e:
             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
             print(f"Unhandled error during KB creation processing: {e}")
             traceback.print_exc()
             return Response({"error": f"Failed to process files: {type(e).__name__}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# <<< AUTH: Refactor to use generic ListCreateAPIView
class ChatSessionListCreateView(generics.ListCreateAPIView):
    """
    Lists chat sessions owned by the authenticated user (GET) or
    creates a new chat session for the authenticated user (POST).
    """
    serializer_class = ChatSessionSerializer
    # <<< AUTH: Inherits IsAuthenticated permission from global settings

    def get_queryset(self):
        """
        This view should return a list of all the chat sessions
        for the currently authenticated user.
        """
        user = self.request.user
        return ChatSession.objects.filter(owner=user).order_by('-created_at')

    def perform_create(self, serializer):
        """
        Associate the chat session with the logged-in user and validate subject.
        """
        subject = self.request.data.get('subject')
        if not subject or subject not in AGENTS:
             # Raise validation error instead of returning Response directly in perform_create
             from rest_framework.exceptions import ValidationError
             raise ValidationError({"error": "Valid 'subject' is required and must exist."})

        # <<< AUTH: Set the owner to the current user
        serializer.save(owner=self.request.user, subject=subject) # Pass subject explicitly if needed by model


# <<< AUTH: Refactor to use generic RetrieveUpdateDestroyAPIView
class ChatSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieves (GET), updates (PATCH), or deletes (DELETE) a specific
    chat session owned by the authenticated user.
    """
    serializer_class = ChatSessionDetailSerializer # Use detail serializer for GET
    # <<< AUTH: Inherits IsAuthenticated permission from global settings
    lookup_field = 'id' # <<< AUTH: Specify lookup field if your URL uses 'id' instead of 'pk'

    def get_queryset(self):
        """
        Ensure users can only access their own chat sessions.
        """
        user = self.request.user
        # The lookup_field ('id' in this case) will be applied to this filtered queryset
        return ChatSession.objects.filter(owner=user)

    # <<< AUTH: Optional: Override update/perform_update if you need custom logic like subject validation on update
    def perform_update(self, serializer):
        # Example: Validate subject if it's being changed
        if 'subject' in serializer.validated_data:
            new_subject = serializer.validated_data['subject']
            if new_subject not in AGENTS:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"error": f"Invalid subject '{new_subject}' provided."})
        serializer.save() # Owner is not changed here, other fields are updated


class QueryView(APIView):
    """Handles user queries for a specific chat (Authenticated)."""
    # <<< AUTH: Inherits IsAuthenticated permission from global settings

    # Async helper method updated for ownership check
    async def _handle_post_async(self, validated_data, user): # <<< AUTH: Accept user
        question = validated_data['question']
        # Subject is taken from the chat session now, not request data directly
        # subject = validated_data['subject'] # <<< Remove subject from direct input if desired
        chat_id = validated_data['chat_id']

        # <<< AUTH: Use updated async DB wrapper to get session AND verify ownership
        chat_session = await _get_chat_session_for_user_async(chat_id, user)

        # Get subject from the validated chat session
        subject = chat_session.subject
        if not subject:
             raise ValueError("Chat session is missing a subject.") # Or handle appropriately
        agent = _get_agent(subject) # Get agent based on session's subject

        # --- Add User Message ---
        await _save_message_async(chat_session, 'user', question)

        response_data = None
        final_answer_to_save = None
        try:
            # --- Get Comprehensive Answer ---
            response_data = await agent.get_comprehensive_answer(question)

            # --- Process SUCCESSFUL response ---
            # (Keep your existing response processing logic)
            if isinstance(response_data, dict) and 'final' in response_data:
                final_answer_to_save = response_data.get("final", "Error: Agent response missing 'final' key.")
            elif isinstance(response_data, str):
                final_answer_to_save = response_data
                print(f"Warning: Agent returned a string instead of dict: {response_data}")
                response_data = {'final': final_answer_to_save, 'rag': 'N/A', 'llm': 'N/A', 'web': 'N/A', 'sources': []}
            else:
                print(f"Agent returned unexpected data type: {type(response_data)}")
                final_answer_to_save = "Error: Agent returned invalid data structure."
                response_data = {'final': final_answer_to_save, 'rag': 'N/A', 'llm': 'N/A', 'web': 'N/A', 'sources': []}
                raise ValueError("Agent returned invalid data structure.")

            # --- Save Assistant Message ---
            await _save_message_async(chat_session, 'assistant', final_answer_to_save)
            return response_data

        except Exception as e:
             print(f"Exception caught within _handle_post_async during agent call: {e}")
             traceback.print_exc()
             error_message = f"Sorry, an internal error occurred: {type(e).__name__}"
             await _save_message_async(chat_session, 'assistant', error_message)
             raise e # Re-raise to be caught by the sync wrapper

    # Synchronous main view method
    def post(self, request, format=None):
        # <<< AUTH: request.user is available
        user = request.user

        request_serializer = QueryRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            print(f"Query validation errors: {request_serializer.errors}")
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = request_serializer.validated_data

        try:
            # <<< AUTH: Pass user to the async handler
            response_data = async_to_sync(self._handle_post_async)(validated_data, user)

            # (Keep your existing post-async validation and response logic)
            if not isinstance(response_data, dict) or not all(k in response_data for k in ['final', 'rag', 'llm', 'web', 'sources']):
                 print(f"Async helper returned unexpected or incomplete data structure: {response_data}")
                 raise ValueError("Internal processing error: Invalid response structure received.")

            response_serializer = QueryResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Http404 as e: # <<< AUTH: Catch 404 if _get_chat_session_for_user_async fails
             print(f"Not Found error during query handling (likely wrong chat_id or not owner): {e}")
             return Response({"error": "Chat session not found or you do not have permission."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
             print(f"Value error during query handling: {e}")
             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) # Or 400 if validation
        except Exception as e:
            print(f"Unhandled error caught in post method: {e}")
            traceback.print_exc()
            return Response({"error": f"Error processing query: {type(e).__name__}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)