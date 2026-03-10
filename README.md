# Portal Lana 🧠

O **Portal Lana** é uma plataforma avançada de Inteligência Artificial Generativa e orquestração de APIs, desenhada para atuar como um assistente corporativo inteligente e centralizado.

O diferencial arquitetural do projeto reside na sua capacidade de **Roteamento Dinâmico de Contexto (Agentic Routing)**. A IA é capaz de interpretar a intenção do usuário no chat e decidir autonomamente qual fonte de dados consultar para formular a melhor resposta.

## 🚀 Arquitetura Híbrida de Dados
O sistema mescla duas das abordagens mais poderosas de recuperação de informação no mesmo fluxo de conversação:

- **RAG (Retrieval-Augmented Generation):** Para buscas semânticas, regras de negócio e dados não estruturados. A IA consulta documentos previamente vetorizados na base de conhecimento.
- **Text-to-SQL (Consulta Operacional):** Para perguntas analíticas e quantitativas. A IA gera dinamicamente queries estruturadas para consultar bancos de dados relacionais e devolver métricas exatas e em tempo real.

## 🏗️ Estrutura Modular
- **`engine` (Motor Administrativo):** Responsável pela ingestão de dados, vetorização de documentos, configurações de LLMs e a lógica de roteamento (Agente).
- **`chat` (Interface de Consumo):** Endpoints de comunicação unificados onde o usuário interage de forma transparente com as múltiplas bases de dados por trás da Lana.

## 🛠️ Stack Tecnológica Base
- **Linguagem:** Python
- **Framework Web:** Django (para roteamento robusto e administração)
- **Banco de Dados Principal:** PostgreSQL
- **Motor Vetorial:** Extensão `pgvector`
- **Integração de IA:** APIs de LLMs (Embeddings, Geração de Texto e Function Calling)

---
*Nota: Este projeto está em fase de desenvolvimento arquitetural. Instruções de setup local, variáveis de ambiente e deploy serão documentadas nas próximas releases.*