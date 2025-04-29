import uuid
import asyncio
try:
    from unittest.mock import patch, MagicMock, AsyncMock
except ImportError:
    from unittest.mock import patch, MagicMock
    AsyncMock = MagicMock # Basic fallback, might not work perfectly for all await cases

from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status

from .models import ChatSession, ChatMessage

VALID_SUBJECT = "Computer Science"
INVALID_SUBJECT = "Astrology"

class SubjectAPITests(APITestCase):
    """Tests for the /api/subjects/ endpoint."""

    def test_list_subjects_success(self):
        """Ensure we can list the configured subjects."""
        url = reverse('subject-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)
        self.assertIn("Computer Science", response.data)
        self.assertIn("Math", response.data)
        self.assertIn("Physics", response.data)
        self.assertEqual(len(response.data), 3)


class ChatSessionAPITests(APITestCase):
    """Tests for /api/chats/ and /api/chats/{chat_id}/ endpoints."""

    def setUp(self):
        self.chat_session = ChatSession.objects.create(name="Initial Chat", subject=VALID_SUBJECT)
        self.detail_url = reverse('chat-detail', args=[self.chat_session.id])

    def test_list_chats_success(self):
        url = reverse('chat-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], str(self.chat_session.id))

    def test_create_chat_success(self):
        url = reverse('chat-list-create')
        data = {'name': 'New Test Chat', 'subject': VALID_SUBJECT}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ChatSession.objects.filter(id=response.data['id']).exists())
        self.assertEqual(ChatSession.objects.count(), 2)

    def test_create_chat_invalid_subject(self):
        url = reverse('chat-list-create')
        data = {'name': 'Invalid Subject Chat', 'subject': INVALID_SUBJECT}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_chat_missing_subject(self):
        url = reverse('chat-list-create')
        data = {'name': 'No Subject Chat'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_chat_detail_success(self):
        ChatMessage.objects.create(chat_session=self.chat_session, role='user', content='Test question')
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.chat_session.id))
        self.assertIn('messages', response.data)
        self.assertEqual(len(response.data['messages']), 1)

    def test_get_chat_detail_not_found(self):
        invalid_id = uuid.uuid4()
        url = reverse('chat-detail', args=[invalid_id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_chat_name_success(self):
        data = {'name': 'Updated Chat Name'}
        response = self.client.patch(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.chat_session.refresh_from_db()
        self.assertEqual(self.chat_session.name, data['name'])

    def test_update_chat_invalid_subject_fail(self):
        data = {'subject': INVALID_SUBJECT}
        response = self.client.patch(self.detail_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_chat_success(self):
        initial_count = ChatSession.objects.count()
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(ChatSession.objects.count(), initial_count - 1)


class KnowledgeBaseAPITests(APITestCase):
    """Basic tests for the /api/subjects/{subject}/kb/ endpoint."""

    def test_kb_upload_no_files_fail(self):
        url = reverse('knowledge-base', args=[VALID_SUBJECT])
        response = self.client.post(url, {}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_kb_upload_invalid_subject_fail(self):
        url = reverse('knowledge-base', args=[INVALID_SUBJECT])
        response = self.client.post(url, {'files': []}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.agent.SubjectAgent.create_knowledge_base', new_callable=AsyncMock) # Use AsyncMock
    def test_kb_upload_success_mocked(self, mock_create_kb):

        url = reverse('knowledge-base', args=[VALID_SUBJECT])
        from django.core.files.uploadedfile import SimpleUploadedFile
        dummy_file = SimpleUploadedFile("test.pdf", b"file_content", content_type="application/pdf")
        data = {'files': [dummy_file]}

        response = self.client.post(url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("message", response.data)
        mock_create_kb.assert_awaited_once() # Check that it was awaited

class QueryAPITests(APITestCase):

    def setUp(self):
        self.chat_session = ChatSession.objects.create(name="Query Test Chat", subject=VALID_SUBJECT)
        self.query_url = reverse('query')
        self.valid_payload = {
            'question': 'What is testing?',
            'subject': VALID_SUBJECT,
            'chat_id': str(self.chat_session.id)
        }

    @patch('api.agent.SubjectAgent.get_comprehensive_answer', new_callable=AsyncMock)
    def test_query_success(self, mock_get_answer):
        """Ensure a successful query returns 200 and expected data."""

        mock_response_dict = {
            'final': 'This is the mocked final answer.',
            'rag': 'Mocked RAG answer.',
            'llm': 'Mocked LLM answer.',
            'web': 'Mocked Web answer.',
            'sources': ['http://mock.url/1']
        }
        mock_get_answer.return_value = mock_response_dict

        response = self.client.post(self.query_url, self.valid_payload, format='json')

        # Assertions
        self.assertEqual(response.status_code, status.HTTP_200_OK) # <<< Check if this passes now
        self.assertIn('final', response.data)
        self.assertEqual(response.data['final'], 'This is the mocked final answer.')
        # ... (other data assertions) ...
        self.assertEqual(response.data['sources'], ['http://mock.url/1'])

        mock_get_answer.assert_awaited_once_with(self.valid_payload['question'])

        self.assertEqual(ChatMessage.objects.count(), 2)
        asst_msg = ChatMessage.objects.filter(chat_session=self.chat_session, role='assistant').first()
        self.assertEqual(asst_msg.content, 'This is the mocked final answer.')


    def test_query_missing_data(self):
        """Ensure query fails with 400 if data is missing."""
        payload = self.valid_payload.copy()
        del payload['question']
        response = self.client.post(self.query_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_query_invalid_chat_id(self):
        """Ensure query fails with 404 if chat_id is invalid."""
        payload = self.valid_payload.copy()
        payload['chat_id'] = str(uuid.uuid4())
        response = self.client.post(self.query_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_query_invalid_subject(self):
        """Ensure query fails with 404 if subject is invalid."""
        payload = self.valid_payload.copy()
        payload['subject'] = INVALID_SUBJECT
        response = self.client.post(self.query_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch('api.agent.SubjectAgent.get_comprehensive_answer', new_callable=AsyncMock)
    def test_query_agent_exception(self, mock_get_answer):
        """Ensure 500 is returned if the agent raises an exception."""

        mock_get_answer.side_effect = ValueError("Agent internal error")

        response = self.client.post(self.query_url, self.valid_payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertIn('error', response.data)

        self.assertEqual(ChatMessage.objects.count(), 2) # User + Error Assistant Msg
        asst_msg = ChatMessage.objects.filter(chat_session=self.chat_session, role='assistant').first()
        self.assertIsNotNone(asst_msg)
        self.assertIn("Sorry, an internal error occurred: ValueError", asst_msg.content)