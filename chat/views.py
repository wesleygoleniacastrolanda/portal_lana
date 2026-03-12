import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import ChatSession, ChatMessage, ChatAgent # <-- Adicionado ChatAgent aqui
from engine.services import chat_with_agent

@csrf_exempt 
def api_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            agent_id = data.get('agent_id')
            user_message = data.get('message')
            session_id = data.get('session_id') 

            # Busca o agente para podermos checar a data de atualização
            try:
                agent = ChatAgent.objects.get(id=agent_id)
            except ChatAgent.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Agente não encontrado."}, status=404)

            # 1. Recupera ou cria uma nova Sessão de Chat
            if session_id:
                session = ChatSession.objects.get(id=session_id)
                
                # 🛑 NOVA TRAVA DE SEGURANÇA (CAMINHO 2) 🛑
                # Se o agente foi editado no admin DEPOIS que este chat começou, nós bloqueamos!
                if agent.updated_at > session.created_at:
                    mensagem_bloqueio = (
                        "⚠️ **Acesso Revogado:** As configurações de bases de dados ou documentos "
                        "deste agente foram alteradas recentemente. Por questões de segurança, "
                        "este chat foi encerrado. **Por favor, inicie um novo chat.**"
                    )
                    return JsonResponse({
                        "status": "success",
                        "session_id": str(session.id),
                        "response": mensagem_bloqueio
                    })
            else:
                session = ChatSession.objects.create(agent_id=agent_id)

            # 2. Salva a pergunta do usuário no banco
            user_msg = ChatMessage.objects.create(session=session, role='user', content=user_message)

            # 3. Busca o histórico da conversa para dar contexto ao LLM
            historico_bd = session.messages.exclude(id=user_msg.id)
            historico_formatado = [{"role": msg.role, "content": msg.content} for msg in historico_bd]

            # 4. Chama o Orquestrador (Motor Principal)
            bot_response = chat_with_agent(agent_id=agent_id, user_message=user_message, history=historico_formatado)

            # 5. Salva a resposta da IA no banco
            ChatMessage.objects.create(session=session, role='assistant', content=bot_response)

            # 6. Devolve a resposta para o Frontend
            return JsonResponse({
                "status": "success",
                "session_id": str(session.id),
                "response": bot_response
            })

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "Apenas método POST é permitido."}, status=405)