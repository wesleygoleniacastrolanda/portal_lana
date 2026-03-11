# engine/admin.py
from django.contrib import admin
from .models import DataSource, KnowledgeBase, KnowledgeChunk, ChatAgent


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ("name", "source_type", "host", "port", "database_name", "is_active", "updated_at")
    list_filter = ("source_type", "is_active")
    search_fields = ("name", "host", "database_name", "username")

# Removemos o registro direto do KnowledgeChunk do menu lateral
# admin.site.unregister(KnowledgeChunk) # Se já estivesse registrado

@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    # Mostra o status com um ícone de Check (V) ou X no painel
    list_display = ('name', 'is_vectorized', 'last_processed_at')
    list_filter = ('is_vectorized',)
    readonly_fields = ('is_vectorized', 'last_processed_at')
    
    actions = ['generate_vectors']

    @admin.action(description='Vetorizar base de conhecimento selecionada')
    def generate_vectors(self, request, queryset):
        from .services import process_knowledge_base
        for kb in queryset:
            process_knowledge_base(kb.id)
        self.message_user(request, "Vetorização concluída com sucesso!")

# Se você ainda quiser ver os chunks, mas APENAS dentro da Base de Conhecimento:
class KnowledgeChunkInline(admin.TabularInline):
    model = KnowledgeChunk
    extra = 0
    readonly_fields = ('content', 'embedding') # O embedding fica oculto ou apenas leitura
    exclude = ('embedding',) # Melhora o visual removendo a lista de números

# Adicione isso na KnowledgeBaseAdmin se quiser ver os textos fatiados lá dentro:
# inlines = [KnowledgeChunkInline]

@admin.register(ChatAgent)
class ChatAgentAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    # O filter_horizontal cria aquela interface visual de duas colunas 
    # no admin do Django, facilitando muito na hora de vincular os M2M!
    filter_horizontal = ('data_sources', 'knowledge_bases')