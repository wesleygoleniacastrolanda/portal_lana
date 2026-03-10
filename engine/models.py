import uuid
from django.db import models
from pgvector.django import VectorField

class KnowledgeBase(models.Model):
    # O código usa 'id', 'name', 'full_text' (Inglês)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nome da Base") 
    description = models.TextField(blank=True, verbose_name="Descrição")
    full_text = models.TextField(verbose_name="Texto de Conhecimento")
    created_at = models.DateTimeField(auto_now_add=True)
    is_vectorized = models.BooleanField(default=False, verbose_name="Vetorizado?")
    last_processed_at = models.DateTimeField(null=True, blank=True, verbose_name="Último Processamento")

    # O método é nativo do Django, mas o retorno é o que aparece na tela
    def __str__(self):
        return self.name

    class Meta:
        # Aqui você "traduz" apenas para o Admin
        verbose_name = "Base de Conhecimento"
        verbose_name_plural = "Bases de Conhecimento"

class KnowledgeChunk(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name="chunks")
    content = models.TextField(verbose_name="Conteúdo do Fragmento")
    embedding = VectorField(dimensions=1536, null=True, blank=True)

    class Meta:
        verbose_name = "Fragmento de Conhecimento"
        verbose_name_plural = "Fragmentos de Conhecimento"