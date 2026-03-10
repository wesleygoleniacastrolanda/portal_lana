import openai
from django.conf import settings
from .models import KnowledgeBase, KnowledgeChunk
from django.utils import timezone

# Configura a chave da OpenAI vinda do seu .env
openai.api_key = settings.OPENAI_API_KEY

def process_knowledge_base(kb_id):
    """
    Pega o texto completo, fatia e gera os embeddings.
    """
    kb = KnowledgeBase.objects.get(id=kb_id)
    
    # 1. Limpeza básica: remove chunks antigos se houver reprocessamento
    kb.chunks.all().delete()

    # 2. Estratégia de Chunking (Simples para começar)
    # Aqui você pode evoluir para algo como RecursiveCharacterTextSplitter do LangChain
    text = kb.full_text
    chunk_size = 1000  # caracteres
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]

    for text_segment in chunks:
        # 3. Gerar o Embedding na OpenAI
        response = openai.embeddings.create(
            input=text_segment,
            model="text-embedding-3-small"
        )
        vector = response.data[0].embedding

        # 4. Salvar o fragmento com o vetor no pgvector
        KnowledgeChunk.objects.create(
            knowledge_base=kb,
            content=text_segment,
            embedding=vector
        )
    kb.is_vectorized = True
    kb.last_processed_at = timezone.now()
    kb.save()