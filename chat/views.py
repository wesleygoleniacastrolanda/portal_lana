import json
from uuid import UUID

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from .models import ChatSession, ChatMessage, ChatAgent
from engine.services import chat_with_agent


@login_required
def chat_ui(request):
    return render(request, 'chat/chat_ui.html')


@login_required
def api_agents(request):
    if request.method != 'GET':
        return JsonResponse({"status": "error", "message": "Apenas método GET é permitido."}, status=405)

    agents = ChatAgent.objects.filter(is_active=True).order_by('name').values('id', 'name')
    return JsonResponse({"status": "success", "agents": list(agents)})


@login_required
def api_sessions(request):
    if request.method != 'GET':
        return JsonResponse({"status": "error", "message": "Apenas método GET é permitido."}, status=405)

    agent_id = request.GET.get('agent_id')
    if not agent_id:
        return JsonResponse({"status": "error", "message": "Parâmetro agent_id é obrigatório."}, status=400)

    sessions = (
        ChatSession.objects
        .filter(agent_id=agent_id)
        .select_related('agent')
        .order_by('-created_at')[:30]
    )

    payload = [
        {
            "id": str(session.id),
            "agent_id": str(session.agent_id),
            "agent_name": session.agent.name,
            "created_at": session.created_at.isoformat(),
        }
        for session in sessions
    ]
    return JsonResponse({"status": "success", "sessions": payload})


@login_required
def api_messages(request):
    if request.method != 'GET':
        return JsonResponse({"status": "error", "message": "Apenas método GET é permitido."}, status=405)

    session_id = request.GET.get('session_id')
    if not session_id:
        return JsonResponse({"status": "error", "message": "Parâmetro session_id é obrigatório."}, status=400)

    try:
        UUID(str(session_id))
    except ValueError:
        return JsonResponse({"status": "error", "message": "session_id inválido."}, status=400)

    try:
        session = ChatSession.objects.select_related('agent').get(id=session_id)
    except ChatSession.DoesNotExist:
        return JsonResponse({"status": "error", "message": "Sessão não encontrada."}, status=404)

    messages = session.messages.order_by('created_at').values('role', 'content', 'created_at')
    payload = [
        {
            "role": msg['role'],
            "content": msg['content'],
            "created_at": msg['created_at'].isoformat(),
        }
        for msg in messages
    ]

    return JsonResponse({
        "status": "success",
        "session": {
            "id": str(session.id),
            "agent_id": str(session.agent_id),
            "agent_name": session.agent.name,
        },
        "messages": payload,
    })

@login_required
@csrf_exempt
def api_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            agent_id = data.get('agent_id')
            user_message = data.get('message')
            session_id = data.get('session_id') 

            if not agent_id or not user_message:
                return JsonResponse(
                    {"status": "error", "message": "agent_id e message são obrigatórios."},
                    status=400,
                )

            # Busca o agente para podermos checar a data de atualização
            try:
                agent = ChatAgent.objects.get(id=agent_id)
            except ChatAgent.DoesNotExist:
                return JsonResponse({"status": "error", "message": "Agente não encontrado."}, status=404)

            # 1. Recupera ou cria uma nova Sessão de Chat
            if session_id:
                try:
                    session = ChatSession.objects.get(id=session_id)
                except ChatSession.DoesNotExist:
                    return JsonResponse({"status": "error", "message": "Sessão não encontrada."}, status=404)

                if str(session.agent_id) != str(agent.id):
                    return JsonResponse({"status": "error", "message": "Sessão não pertence ao agente informado."}, status=400)
                
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
                        "response": mensagem_bloqueio,
                        "response_created_at": timezone.now().isoformat(),
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
            assistant_msg = ChatMessage.objects.create(session=session, role='assistant', content=bot_response)

            # 6. Devolve a resposta para o Frontend
            return JsonResponse({
                "status": "success",
                "session_id": str(session.id),
                "response": bot_response,
                "response_created_at": assistant_msg.created_at.isoformat(),
            })

        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
            
    return JsonResponse({"status": "error", "message": "Apenas método POST é permitido."}, status=405)