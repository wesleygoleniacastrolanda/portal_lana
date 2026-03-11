import uuid
from django.db import models
from pgvector.django import VectorField


class DataSource(models.Model):
    class DataSourceType(models.TextChoices):
        MYSQL = "mysql", "MySQL"
        POSTGRES = "postgres", "PostgreSQL"
        ORACLE = "oracle", "Oracle"
        SAP = "sap", "SAP"
        SQLSERVER = "sqlserver", "SQL Server"
        SQLITE = "sqlite", "SQLite"
        OTHER = "other", "Outro"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, verbose_name="Nome da Conexão")
    source_type = models.CharField(
        max_length=20,
        choices=DataSourceType.choices,
        verbose_name="Tipo de Banco",
    )
    host = models.CharField(max_length=255, blank=True, verbose_name="Host")
    port = models.PositiveIntegerField(null=True, blank=True, verbose_name="Porta")
    database_name = models.CharField(max_length=255, blank=True, verbose_name="Nome do Banco")
    username = models.CharField(max_length=255, blank=True, verbose_name="Usuário")
    password = models.CharField(max_length=255, blank=True, verbose_name="Senha")
    connection_params = models.JSONField(default=dict, blank=True, verbose_name="Parâmetros Extras")
    is_active = models.BooleanField(default=True, verbose_name="Ativo?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"

    class Meta:
        verbose_name = "Fonte de Dado"
        verbose_name_plural = "Fontes de Dados"

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

class ChatAgent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name="Nome do Agente/Chat")
    
    # O System Prompt é excelente para você dar uma "personalidade" ou regras específicas 
    # para cada agente (ex: "Você é um assistente de RH, responda de forma formal...").
    system_prompt = models.TextField(
        blank=True, 
        verbose_name="Instruções de Comportamento (Prompt)",
        help_text="Regras de como este agente deve se comportar."
    )
    
    # --- AS RELAÇÕES MÁGICAS ---
    # ManyToMany permite que um agente acesse vários bancos/bases, 
    # e que um banco/base seja usado por vários agentes.
    data_sources = models.ManyToManyField(
        DataSource, 
        blank=True, 
        related_name="agents",
        verbose_name="Bancos de Dados Vinculados"
    )
    knowledge_bases = models.ManyToManyField(
        KnowledgeBase, 
        blank=True, 
        related_name="agents",
        verbose_name="Bases de Conhecimento (RAG) Vinculadas"
    )
    
    is_active = models.BooleanField(default=True, verbose_name="Ativo?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Agente de Chat"
        verbose_name_plural = "Agentes de Chat"