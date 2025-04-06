# api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('subjects/', views.SubjectListView.as_view(), name='subject-list'),
    path('subjects/<str:subject>/kb/', views.KnowledgeBaseView.as_view(), name='knowledge-base'),
    path('chats/', views.ChatSessionListView.as_view(), name='chat-list-create'),
    path('chats/<uuid:chat_id>/', views.ChatSessionDetailView.as_view(), name='chat-detail'),
    # If you want messages as a sub-resource:
    # path('chats/<uuid:chat_id>/messages/', views.ChatMessageListView.as_view(), name='message-list'),
    path('query/', views.QueryView.as_view(), name='query'),
]