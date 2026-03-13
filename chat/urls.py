from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_ui, name='chat_ui'),
    path('api/agents/', views.api_agents, name='api_agents'),
    path('api/sessions/', views.api_sessions, name='api_sessions'),
    path('api/messages/', views.api_messages, name='api_messages'),
    path('api/send-message/', views.api_chat, name='api_chat'),
]