from django.urls import path
from . import views

urlpatterns = [
    path('subjects/', views.SubjectListView.as_view(), name='subject-list'),
    path('subjects/<str:subject>/kb/', views.KnowledgeBaseView.as_view(), name='knowledge-base'),
    path('chats/', views.ChatSessionListCreateView.as_view(), name='chat-list-create'), # Changed name for consistency

    path('chats/<uuid:id>/', views.ChatSessionDetailView.as_view(), name='chat-detail'),

    path('query/', views.QueryView.as_view(), name='query'),
]