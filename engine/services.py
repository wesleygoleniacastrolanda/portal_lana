import openai
from django.conf import settings
from sqlalchemy import create_engine, inspect, text
from .models import KnowledgeBase, KnowledgeChunk, DataSource, ChatAgent
from django.utils import timezone
from pgvector.django import CosineDistance
import json
import re

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

def search_knowledge(kb_id, user_query, limit=3):
    """
    Transforms the user query into a vector and searches for the most similar chunks in pgvector.
    Returns a unified text with the found snippets.
    """
    # 1. Transform user query into a vector using the SAME model
    response = openai.embeddings.create(
        input=user_query,
        model="text-embedding-3-small"
    )
    query_vector = response.data[0].embedding

    # 2. Magic Database Search (pgvector)
    # Filter by the correct knowledge base and order by similarity (lowest cosine distance)
    similar_chunks = KnowledgeChunk.objects.filter(
        knowledge_base_id=kb_id
    ).order_by(
        CosineDistance('embedding', query_vector)
    )[:limit] # Get only the top `limit` most relevant chunks

    # 3. Join found texts to deliver to the LLM later
    found_texts = []
    for chunk in similar_chunks:
        found_texts.append(f"Found Snippet:\n{chunk.content}")
    
    final_context = "\n\n---\n\n".join(found_texts)
    
    return final_context

def build_db_url(datasource):
    """
    Helper function to build the SQLAlchemy connection URL based on the database type.
    """
    # Usamos pymysql para MySQL e psycopg2 para Postgres (drivers padrão do Python)
    driver_mapping = {
        'mysql': 'mysql+pymysql',
        'postgres': 'postgresql+psycopg2',
        # Adicione outros conforme a necessidade (sqlserver, oracle...)
    }
    
    driver = driver_mapping.get(datasource.source_type, datasource.source_type)
    
    # Monta a URL no formato: dialect+driver://username:password@host:port/database
    url = f"{driver}://{datasource.username}:{datasource.password}@{datasource.host}:{datasource.port}/{datasource.database_name}"
    return url

def extract_database_schema(datasource_id):
    """
    Connects to the specified DataSource, extracts table and column information,
    and returns a formatted string for the LLM.
    """
    try:
        datasource = DataSource.objects.get(id=datasource_id)
        db_url = build_db_url(datasource)
        
        # Cria a engine de conexão do SQLAlchemy
        engine = create_engine(db_url)
        
        # O 'inspector' é a ferramenta do SQLAlchemy que lê o schema do banco
        inspector = inspect(engine)
        
        schema_lines = [f"Schema for database '{datasource.database_name}' ({datasource.source_type}):\n"]
        
        # Pega todas as tabelas do banco
        for table_name in inspector.get_table_names():
            schema_lines.append(f"Table: {table_name}")
            columns = inspector.get_columns(table_name)
            
            # Pega as colunas de cada tabela
            for col in columns:
                col_name = col['name']
                col_type = str(col['type'])
                schema_lines.append(f"  - {col_name} ({col_type})")
                
            schema_lines.append("") # Linha em branco para separar as tabelas
            
        return "\n".join(schema_lines)
        
    except Exception as e:
        return f"Error extracting schema: {str(e)}"
    
def generate_sql_query(schema_text, user_query, dialect):
    """
    Pede para o LLM traduzir a pergunta do usuário em uma query SQL válida.
    """
    system_prompt = f"""
    You are an expert Data Analyst and SQL developer.
    Your task is to write a SQL query for a {dialect} database that answers the user's question.
    
    CRITICAL RULES:
    1. Return ONLY the raw SQL query. Do not include markdown formatting like ```sql or explanations.
    2. ALWAYS append a LIMIT 50 to the end of your query to prevent huge data dumps.
    3. Use only the tables and columns provided in the schema below.
    
    SCHEMA:
    {schema_text}
    """

    response = openai.chat.completions.create(
        model="gpt-4o", # Recomendo fortemente um modelo mais inteligente (GPT-4) para escrever código SQL
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        temperature=0.0 # Temperatura zero para ele ser determinístico e não inventar moda
    )
    
    # Limpa a resposta caso o LLM teimosamente coloque formatação Markdown
    raw_sql = response.choices[0].message.content.strip()
    raw_sql = re.sub(r"```sql", "", raw_sql)
    raw_sql = re.sub(r"```", "", raw_sql).strip()
    
    return raw_sql

def query_database(datasource_id, user_query):
    """
    Orquestra o Text-to-SQL: Extrai schema, gera a query, executa no banco e retorna os dados.
    """
    try:
        # 1. Busca os dados da conexão e o schema
        datasource = DataSource.objects.get(id=datasource_id)
        schema_text = extract_database_schema(datasource_id)
        
        # 2. Pede pro LLM gerar a query SQL
        sql_query = generate_sql_query(schema_text, user_query, datasource.source_type)
        print(f"--- QUERY GERADA PELO LLM ---\n{sql_query}\n-----------------------------")
        
        # 3. Conecta no banco e executa a query gerada
        db_url = build_db_url(datasource)
        engine = create_engine(db_url)
        
        # Usamos engine.connect() para abrir uma sessão e text() para rodar SQL cru com segurança
        with engine.connect() as connection:
            result = connection.execute(text(sql_query))
            
            # 4. Formata o resultado
            # Pega o nome das colunas
            column_names = result.keys() 
            # Pega as linhas e transforma em uma lista de dicionários
            rows = [dict(zip(column_names, row)) for row in result.fetchall()]
            
            if not rows:
                return "A consulta foi executada com sucesso, mas não retornou nenhum dado."
                
            # Transforma o resultado em uma string formatada (ex: JSON) para entregar ao LLM principal depois
            import json
            return f"Resultados da Consulta ao banco '{datasource.name}':\n" + json.dumps(rows, default=str, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"\n🚨 ERRO INTERNO NA FUNÇÃO SQL: {str(e)}\n") 
        return f"Erro ao consultar o banco de dados: {str(e)}"

# --- NOVAS FUNÇÕES DE VALIDAÇÃO DE ACESSO ---

def get_agent_access_map(agent):
    """
    Retorna os IDs autorizados ATUALMENTE para este agente.
    Avaliado a cada requisição para refletir mudanças do painel na hora.
    """
    allowed_kb_ids = set(
        str(kb_id) for kb_id in agent.knowledge_bases.filter(is_vectorized=True).values_list("id", flat=True)
    )
    allowed_datasource_ids = set(
        str(ds_id) for ds_id in agent.data_sources.filter(is_active=True).values_list("id", flat=True)
    )
    return {
        "knowledge_base_ids": allowed_kb_ids,
        "datasource_ids": allowed_datasource_ids,
    }

def has_revoked_access_in_history(history, access_map):
    """
    Varre o histórico procurando chamadas de ferramentas antigas 
    que usaram IDs que o agente não tem mais acesso.
    """
    for msg in history:
        tool_calls = msg.get("tool_calls", []) if isinstance(msg, dict) else getattr(msg, "tool_calls", [])
        
        if not tool_calls:
            continue
            
        for tool_call in tool_calls:
            if isinstance(tool_call, dict):
                function_name = tool_call.get("function", {}).get("name")
                arguments_str = tool_call.get("function", {}).get("arguments", "{}")
            else:
                function_name = tool_call.function.name
                arguments_str = tool_call.function.arguments
            
            try:
                args = json.loads(arguments_str)
            except json.JSONDecodeError:
                continue
                
            if function_name == "search_knowledge":
                kb_id = str(args.get("kb_id", ""))
                if kb_id and kb_id not in access_map["knowledge_base_ids"]:
                    return True 
                    
            elif function_name == "query_database":
                datasource_id = str(args.get("datasource_id", ""))
                if datasource_id and datasource_id not in access_map["datasource_ids"]:
                    return True 
                    
    return False

# ---------------------------------------------

def build_agent_tools(agent):
    """
    Constrói o esquema JSON (Cardápio de Ferramentas) baseado no que o Agente tem acesso.
    """
    tools = []
    
    # 1. Verifica se o Agente tem Bases de Conhecimento (RAG) vinculadas
    knowledge_bases = agent.knowledge_bases.filter(is_vectorized=True)
    if knowledge_bases.exists():
        kb_descriptions = ", ".join([f"ID '{kb.id}' para '{kb.name}'" for kb in knowledge_bases])
        kb_ids = [str(kb.id) for kb in knowledge_bases]
        
        tools.append({
            "type": "function",
            "function": {
                "name": "search_knowledge",
                "description": "Busca informações em manuais, regras de negócio, normas e documentos em texto da cooperativa.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "kb_id": {
                            "type": "string",
                            "enum": kb_ids,
                            "description": f"Obrigatório. O ID da base de conhecimento. Opções disponíveis: {kb_descriptions}."
                        },
                        "user_query": {
                            "type": "string",
                            "description": "A pergunta do usuário reescrita de forma otimizada para buscar nos documentos."
                        }
                    },
                    "required": ["kb_id", "user_query"]
                }
            }
        })

    # 2. Verifica se o Agente tem Bancos de Dados (SQL) vinculados
    data_sources = agent.data_sources.filter(is_active=True)
    if data_sources.exists():
        db_descriptions = ", ".join([f"ID '{db.id}' para '{db.name}'" for db in data_sources])
        db_ids = [str(db.id) for db in data_sources]
        
        tools.append({
            "type": "function",
            "function": {
                "name": "query_database",
                "description": "Consulta o banco de dados para buscar qualquer tipo de registro, como chamados, cadastros de clientes/cooperados, métricas, relatórios ou informações financeiras.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "datasource_id": {
                            "type": "string",
                            "enum": db_ids,
                            "description": f"Obrigatório. O ID do banco de dados. Opções disponíveis: {db_descriptions}."
                        },
                        "user_query": {
                            "type": "string",
                            "description": "A pergunta exata do usuário."
                        }
                    },
                    "required": ["datasource_id", "user_query"]
                }
            }
        })
        
    return tools

def chat_with_agent(agent_id, user_message, history=None):
    """
    O Orquestrador Principal. Recebe a mensagem, consulta o LLM, roda as ferramentas e retorna a resposta.
    """
    if history is None:
        history = []

    # 👇 ADICIONE ESTE PRINT PARA VER O QUE A SUA VIEW ESTÁ MANDANDO 👇
    print("\n--- FORMATO DO HISTÓRICO RECEBIDO ---")
    print(json.dumps(history, indent=2, ensure_ascii=False))
    print("--------------------------------------\n")  

    agent = ChatAgent.objects.get(id=agent_id)
    tools = build_agent_tools(agent)
    access_map = get_agent_access_map(agent)

    # --- DEBUG PRINTS ---
    print("\n" + "="*50)
    print(f"🔍 DEBUG DE ACESSOS DO AGENTE [{agent.name}]:")
    print(f"📚 Bases de Conhecimento Ativas: {access_map['knowledge_base_ids'] if access_map['knowledge_base_ids'] else 'NENHUMA'}")
    print(f"🗄️ Bancos de Dados Ativos: {access_map['datasource_ids'] if access_map['datasource_ids'] else 'NENHUM'}")
    print("="*50 + "\n")

    # --- TRAVA DE SEGURANÇA NO HISTÓRICO ---
    if has_revoked_access_in_history(history, access_map):
        return (
            "⚠️ **Acesso Revogado:** As permissões de leitura deste chat foram alteradas "
            "(bases de dados ou documentos foram removidos do agente). "
            "Por questões de segurança e para evitar o uso de dados em cache, "
            "por favor, **inicie um novo chat**."
        )

    # 1. Coloca a regra do Agente (System Prompt) primeiro
    messages = [{"role": "system", "content": agent.system_prompt}]
    
    # 2. Injeta o histórico de mensagens antigas
    messages.extend(history)
    
    # 3. Adiciona a nova mensagem do usuário no final
    messages.append({"role": "user", "content": user_message})
    
    # Passo 1: Envia para o LLM decidir o que fazer
    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools if tools else None,
        tool_choice="auto" if tools else "none",
        temperature=0.2
    )
    
    response_message = response.choices[0].message

    # Passo 2: O LLM decidiu usar alguma ferramenta? (Roteamento)
    if response_message.tool_calls:
        messages.append(response_message)
        
        for tool_call in response_message.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            print(f"🤖 O Agente decidiu usar a ferramenta: {function_name} com os argumentos: {function_args}")
            
            # Executa a função Python correspondente (Com trava dupla de segurança de ID)
            if function_name == "search_knowledge":
                kb_id = str(function_args.get("kb_id", ""))
                if kb_id in access_map["knowledge_base_ids"]:
                    function_response = search_knowledge(kb_id=kb_id, user_query=function_args.get("user_query"))
                else:
                    function_response = "ERRO: Acesso negado a esta Base de Conhecimento."
                    
            elif function_name == "query_database":
                ds_id = str(function_args.get("datasource_id", ""))
                if ds_id in access_map["datasource_ids"]:
                    function_response = query_database(datasource_id=ds_id, user_query=function_args.get("user_query"))
                else:
                    function_response = "ERRO: Acesso negado a este Banco de Dados."
            else:
                function_response = "Ferramenta desconhecida."
                
            # Passo 3: Devolve o resultado da ferramenta para o LLM
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": str(function_response),
            })
            
        # Passo 4: O LLM lê os dados e formula a resposta final
        final_response = openai.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.4
        )
        return final_response.choices[0].message.content

    return response_message.content