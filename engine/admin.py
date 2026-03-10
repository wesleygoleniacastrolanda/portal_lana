# engine/admin.py
from django.contrib import admin
from .models import KnowledgeBase, KnowledgeChunk

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