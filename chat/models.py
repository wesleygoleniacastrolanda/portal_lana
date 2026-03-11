import uuid
from django.db import models
from engine.models import ChatAgent # Ajuste o import conforme sua estrutura

class ChatSession(models.Model):
    """Representa uma 'janela' de conversa entre um usuário e um Agente."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(ChatAgent, on_delete=models.CASCADE, related_name="sessions")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Sessão {self.id} com {self.agent.name}"

class ChatMessage(models.Model):
    """Guarda o vai-e-vem das mensagens (Usuário e IA)."""
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, verbose_name="Papel (user ou assistant)")
    content = models.TextField(verbose_name="Conteúdo da Mensagem")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # Garante que o histórico venha na ordem certa temporalmente

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."