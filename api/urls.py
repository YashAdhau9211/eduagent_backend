# api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('subjects/', views.SubjectListView.as_view(), name='subject-list'),
    path('subjects/<str:subject>/kb/', views.KnowledgeBaseView.as_view(), name='knowledge-base'),
    path('chats/', views.ChatSessionListCreateView.as_view(), name='chat-list-create'), # Changed name for consistency

    # <<< AUTH: Change <uuid:chat_id> to <uuid:id> to match the view's lookup_field
    path('chats/<uuid:id>/', views.ChatSessionDetailView.as_view(), name='chat-detail'),

    # If you want messages as a sub-resource (keep commented unless implemented):
    # path('chats/<uuid:id>/messages/', views.ChatMessageListView.as_view(), name='message-list'), # Also use id here

    path('query/', views.QueryView.as_view(), name='query'),
]