import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ChatSession, ChatMessage
from engine.services import chat_with_agent # A função que criamos no Bucket 4!

@csrf_exempt # Desabilita CSRF apenas para facilitar o teste da API (em prod, use Token/JWT)
def api_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            agent_id = data.get('agent_id')
            user_message = data.get('message')
            session_id = data.get('session_id') # Pode vir vazio se for uma nova conversa

            # 1. Recupera ou cria uma nova Sessão de Chat
            if session_id:
                session = ChatSession.objects.get(id=session_id)
            else:
                session = ChatSession.objects.create(agent_id=agent_id)

            # 2. Salva a pergunta do usuário no banco
            ChatMessage.objects.create(session=session, role='user', content=user_message)

            # 3. Busca o histórico da conversa para dar contexto ao LLM
            # Transformamos as mensagens do banco em um formato que a OpenAI entende
            historico_bd = session.messages.all()
            historico_formatado = [{"role": msg.role, "content": msg.content} for msg in historico_bd]

            # 4. Chama o Orquestrador (Motor Principal)
            # Dica: Você precisará adaptar a sua função `chat_with_agent` para aceitar 
            # esse `historico_formatado` e incluí-lo antes de enviar para a OpenAI.
            bot_response = chat_with_agent(agent_id=agent_id, user_message=user_message, history=historico_formatado)

            # 5. Salva a resposta da IA no banco
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)

            # 6. Devolve a resposta para o Frontend (incluindo o session_id para ele mandar na próxima)
            return JsonResponse({
                "status": "success",
                "session_id": str(session.id),
                "response": bot_response
            })

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "Apenas método POST é permitido."}, status=405)