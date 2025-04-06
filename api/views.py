# api/views.py
import asyncio
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, parsers
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.conf import settings # To access settings like CHROMA_DB_ROOT_DIR
import tempfile
import os
import traceback
import shutil # For cleanup
from asgiref.sync import async_to_sync, sync_to_async # Import async_to_sync and sync_to_async

# Import your agent and models/serializers
from .agent import SubjectAgent
from .models import ChatSession, ChatMessage
from .serializers import (
    ChatSessionSerializer, ChatSessionDetailSerializer, ChatMessageSerializer,
    QueryRequestSerializer, QueryResponseSerializer
)

# --- Agent Instantiation ---
# Simple global instantiation (NOT suitable for production - thread safety/scaling issues)
AGENTS = {
    subject: SubjectAgent(subject)
    for subject in ["Computer Science", "Math", "Physics"] # Make this dynamic if needed
}
print("Initialized Agents:", list(AGENTS.keys()))

# Helper to get agent or raise 404 (Keep sync)
def _get_agent(subject):
    agent = AGENTS.get(subject)
    if not agent:
        raise Http404(f"Subject agent '{subject}' not found.")
    return agent

# --- Async DB Wrappers ---
# Wrap synchronous ORM methods needed inside async functions
@sync_to_async
def _save_message_async(chat_session, role, content):
    # Ensure content is not excessively long if there's a DB limit
    max_length = 10000 # Example limit, adjust based on your TextField
    truncated_content = content[:max_length] if content else ""
    if len(content) > max_length:
        print(f"Warning: Truncating assistant message for chat {chat_session.id}")
        truncated_content += " ... [truncated]"
    try:
        ChatMessage.objects.create(chat_session=chat_session, role=role, content=truncated_content)
    except Exception as db_e:
        print(f"Error saving message to DB for chat {chat_session.id}: {db_e}")
        traceback.print_exc() # Log the error, but don't crash the request


@sync_to_async
def _get_chat_session_async(chat_id):
    # Use get_object_or_404 within the sync wrapper to handle not found
    # It will raise Http404 if not found, which propagates correctly
    return get_object_or_404(ChatSession, pk=chat_id)

# These are not currently used in async contexts but kept for potential future use
@sync_to_async
def _create_chat_session_async(name, subject):
    return ChatSession.objects.create(name=name, subject=subject)

@sync_to_async
def _get_all_chat_sessions_async():
    # Execute the query and convert to list within the sync wrapper
    return list(ChatSession.objects.all().order_by('-created_at'))

@sync_to_async
def _update_chat_session_async(session, data):
    # Need to pass instance and data to serializer save method
    serializer = ChatSessionSerializer(session, data=data, partial=True)
    serializer.is_valid(raise_exception=True) # Raise validation error if invalid
    return serializer.save()

@sync_to_async
def _delete_chat_session_async(session):
    session.delete()

# --- API Views ---

class SubjectListView(APIView):
    """Lists available subjects."""
    # Keep sync - simple data retrieval
    def get(self, request, format=None):
        return Response(list(AGENTS.keys()), status=status.HTTP_200_OK)


class KnowledgeBaseView(APIView):
    """Handles knowledge base creation (file uploads)."""
    parser_classes = [parsers.MultiPartParser]

    # Async helper for the core logic
    async def _handle_kb_upload_async(self, agent, files):
        temp_dir = tempfile.mkdtemp()
        print(f"Created temporary directory for KB upload: {temp_dir}")
        # Store paths as expected by the updated utils.process_documents
        saved_file_paths = []
        try:
            # --- File Saving (using executor for potentially blocking I/O) ---
            loop = asyncio.get_running_loop()
            for uploaded_file in files:
                if uploaded_file.size > getattr(settings, 'MAX_UPLOAD_SIZE_MB', 50) * 1024 * 1024:
                     raise ValueError(f"File '{uploaded_file.name}' exceeds size limit.")
                # Add content type validation if needed

                path = os.path.join(temp_dir, uploaded_file.name)
                print(f"Saving temporary file: {path}")
                with open(path, "wb") as f:
                    for chunk in uploaded_file.chunks():
                       # Run synchronous file write in executor
                       await loop.run_in_executor(None, f.write, chunk)
                saved_file_paths.append(path)

            if not saved_file_paths:
                 raise ValueError("No valid files were processed for upload.")

            # --- Call Agent Method (already async) ---
            print(f"Calling create_knowledge_base for {agent.subject} with {len(saved_file_paths)} file paths.")
            # create_knowledge_base itself runs process_documents in an executor
            await agent.create_knowledge_base(saved_file_paths)

            # Return success indicator, not a DRF Response
            return {"message": f"Knowledge base update task completed for {agent.subject}"}

        except Exception as e:
             print(f"Error during async KB handling: {e}")
             traceback.print_exc()
             # Re-raise the exception to be caught by the sync wrapper
             raise e
        finally:
             # --- Cleanup ---
             if os.path.exists(temp_dir):
                 try:
                    print(f"Cleaning up temporary directory: {temp_dir}")
                    # Run blocking shutil.rmtree in executor
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, shutil.rmtree, temp_dir)
                 except Exception as cleanup_e:
                    print(f"Error cleaning up temporary directory {temp_dir}: {cleanup_e}")


    # Synchronous view method that DRF calls
    def post(self, request, subject, format=None):
        try:
             agent = _get_agent(subject) # Sync call
        except Http404 as e:
             return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        files = request.FILES.getlist('files')
        if not files:
            return Response({"error": "No files provided."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Run the async helper using async_to_sync
            result_data = async_to_sync(self._handle_kb_upload_async)(agent, files)
            # If successful, return OK. Consider 202 if agent queues the task.
            return Response(result_data, status=status.HTTP_200_OK)

        except ValueError as e: # Catch specific validation errors from helper
             return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
             # Catch any other exceptions from the async helper
             print(f"Unhandled error during KB creation processing: {e}")
             traceback.print_exc()
             return Response({"error": f"Failed to process files: {type(e).__name__}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ChatSessionListView(APIView):
    """Lists chats or creates a new chat."""

    # Keep sync for simplicity unless DB access becomes bottleneck
    def get(self, request, format=None):
        # Add filtering by user in a real application
        sessions = ChatSession.objects.all().order_by('-created_at')
        serializer = ChatSessionSerializer(sessions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    # Keep sync for simplicity unless DB access becomes bottleneck
    def post(self, request, format=None):
        name = request.data.get('name', 'New Chat')
        subject = request.data.get('subject')

        # Basic validation
        if not subject or subject not in AGENTS:
             return Response({"error": "Valid 'subject' is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Sync ORM call is okay here for simplicity
        session = ChatSession.objects.create(name=name, subject=subject)

        serializer = ChatSessionSerializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class ChatSessionDetailView(APIView):
    """Retrieves, updates, or deletes a specific chat session."""

    # Keep sync
    def get(self, request, chat_id, format=None):
        session = get_object_or_404(ChatSession, pk=chat_id)
        serializer = ChatSessionDetailSerializer(session) # Includes messages
        return Response(serializer.data, status=status.HTTP_200_OK)

    # Keep sync
    def patch(self, request, chat_id, format=None):
         session = get_object_or_404(ChatSession, pk=chat_id)
         serializer = ChatSessionSerializer(session, data=request.data, partial=True)
         if serializer.is_valid():
              # Ensure subject remains valid if changed
              if 'subject' in serializer.validated_data and serializer.validated_data['subject'] not in AGENTS:
                   return Response({"error": f"Invalid subject '{serializer.validated_data['subject']}' provided."}, status=status.HTTP_400_BAD_REQUEST)
              serializer.save() # Sync ORM call
              return Response(serializer.data)
         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Keep sync
    def delete(self, request, chat_id, format=None):
         session = get_object_or_404(ChatSession, pk=chat_id)
         session.delete() # Sync ORM call
         return Response(status=status.HTTP_204_NO_CONTENT)


class QueryView(APIView):
    """Handles user queries for a specific chat and subject."""

    # Async helper method containing the core async logic
    async def _handle_post_async(self, validated_data):
        question = validated_data['question']
        subject = validated_data['subject']
        chat_id = validated_data['chat_id']

        # Use await with the async DB wrapper
        chat_session = await _get_chat_session_async(chat_id)
        agent = _get_agent(subject) # Sync helper is fine

        # --- Add User Message ---
        await _save_message_async(chat_session, 'user', question)

        response_data = None
        final_answer_to_save = None
        try:
            # --- Get Comprehensive Answer ---
            response_data = await agent.get_comprehensive_answer(question)

            # --- Process SUCCESSFUL response ---
            if isinstance(response_data, dict) and 'final' in response_data:
                final_answer_to_save = response_data.get("final", "Error: Agent response missing 'final' key.")
            elif isinstance(response_data, str):
                final_answer_to_save = response_data
                print(f"Warning: Agent returned a string instead of dict: {response_data}")
                response_data = {'final': final_answer_to_save, 'rag': 'N/A', 'llm': 'N/A', 'web': 'N/A', 'sources': []}
            else:
                print(f"Agent returned completely unexpected data type: {type(response_data)}")
                final_answer_to_save = "Error: Agent returned invalid data structure."
                response_data = {'final': final_answer_to_save, 'rag': 'N/A', 'llm': 'N/A', 'web': 'N/A', 'sources': []}
                # Raise error to be caught by outer block
                raise ValueError("Agent returned invalid data structure.")

            # --- Save Assistant Message ---
            await _save_message_async(chat_session, 'assistant', final_answer_to_save)
            return response_data # Return the dict

        except Exception as e:
             # --- Handle Exception from agent.get_comprehensive_answer ---
             print(f"Exception caught within _handle_post_async during agent call: {e}")
             traceback.print_exc()
             error_message = f"Sorry, an internal error occurred: {type(e).__name__}"
             # Save the error message
             await _save_message_async(chat_session, 'assistant', error_message)
             # Re-raise the exception so the sync wrapper knows it failed
             raise e


    # Synchronous main view method that DRF calls
    def post(self, request, format=None):
        request_serializer = QueryRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            print(f"Query validation errors: {request_serializer.errors}")
            return Response(request_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        validated_data = request_serializer.validated_data

        try:
            # Call the async helper using async_to_sync
            response_data = async_to_sync(self._handle_post_async)(validated_data)

            # --- Validation after async_to_sync ---
            # Check if the data structure is suitable for the final serializer
            if not isinstance(response_data, dict) or not all(k in response_data for k in ['final', 'rag', 'llm', 'web', 'sources']):
                 print(f"Async helper returned unexpected or incomplete data structure: {response_data}")
                 # This indicates a logic error in _handle_post_async's return value on success path
                 raise ValueError("Internal processing error: Invalid response structure received.")

            # --- Serialize and return success ---
            response_serializer = QueryResponseSerializer(response_data)
            return Response(response_serializer.data, status=status.HTTP_200_OK)

        # --- Specific Exception Handling ---
        except Http404 as e:
             print(f"Not Found error during query handling: {e}")
             # Error wasn't saved to chat because it happened before agent call
             # Decide if 404s should be logged to chat - probably not.
             return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)

        except ValueError as e: # Catch validation errors (malformed response structure check)
             print(f"Value error during query handling: {e}")
             # Error message should have been saved inside _handle_post_async's except block
             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e: # Catch any other exceptions propagated from async_to_sync
            print(f"Unhandled error caught in post method: {e}")
            traceback.print_exc()
            # Error message should have been saved inside _handle_post_async's except block
            return Response({"error": f"Error processing query: {type(e).__name__}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Removed _log_error_to_chat helper as logging is now inside _handle_post_async's except block