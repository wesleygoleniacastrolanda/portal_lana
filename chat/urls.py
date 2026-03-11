from django.urls import path
from . import views

urlpatterns = [
    path('api/send-message/', views.api_chat, name='api_chat'),
]