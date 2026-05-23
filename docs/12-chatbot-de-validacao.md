# Chatbot de Validação

O documento oficial do BuscaAI prevê, como entregável da fase de POC, um **protótipo de chatbot** integrado ao framework. Este arquivo explica o que é esse chatbot, como ele funciona, e por que ele existe.

---

## Por que um chatbot

O BuscaAI é um framework — uma coleção de ferramentas para desenvolvedores. Frameworks são difíceis de avaliar em abstrato. Para demonstrar que o framework funciona e medir sua qualidade de forma concreta, precisa-se de uma **aplicação real rodando sobre ele**.

O chatbot cumpre esse papel: é a interface de teste onde um usuário real faz perguntas em linguagem natural sobre uma base de dados real, e o sistema responde com base nos documentos recuperados. É onde as métricas de RAGAS deixam de ser números abstratos e viram uma conversa que funciona ou não.

O documento do projeto define esse chatbot como o ambiente para:

- Avaliar o tempo de resposta do sistema
- Medir a acurácia semântica das respostas
- Validar a mitigação de alucinações pelo RAG
- Demonstrar o funcionamento em bases de dados heterogêneas

---

## O que o chatbot é

É uma aplicação simples que:

1. Recebe a pergunta do usuário em linguagem natural
2. Chama o endpoint `/chat` do BuscaAI
3. Mostra a resposta gerada pela LLM
4. Mostra as fontes usadas (os chunks recuperados)
5. Mantém o histórico da conversa

```
Usuário:  "Qual o prazo de rescisão do contrato?"
          ↓
      POST /chat
          ↓
BuscaAI: pré-filtragem → busca híbrida → reranker → LLM
          ↓
Sistema:  "O prazo de rescisão é de 30 dias, conforme
           cláusula 8.2 do contrato. O aviso prévio deve
           ser dado por escrito."

          Fontes:
          [1] contrato.pdf, página 3 (score: 0.97)
          [2] contrato.pdf, página 4 (score: 0.89)

Usuário:  "E qual a multa por descumprimento?"
          ↓
      POST /chat  (com histórico)
          ↓
Sistema:  "A multa por descumprimento do prazo de rescisão
           é de 10% do valor total do contrato."
```

---

## Como o histórico de conversa funciona

O endpoint `/chat` recebe a query e o histórico das mensagens anteriores. O grafo de chat do LangGraph tem uma etapa de **reformulação da query** que usa esse histórico para tornar a pergunta independente de contexto antes de buscar.

```
Histórico:
  user: "qual o prazo de rescisão?"
  assistant: "O prazo é de 30 dias..."

Nova query: "e a multa?"

Reformulação: "qual a multa por descumprimento do prazo de rescisão?"
              ↑ agora a query tem contexto suficiente para buscar
```

Sem essa reformulação, "e a multa?" não encontraria nada relevante na base — é vaga demais sozinha.

### Requisição com histórico

```json
POST /chat
{
    "query": "e a multa?",
    "historico": [
        {
            "role": "user",
            "content": "qual o prazo de rescisão?"
        },
        {
            "role": "assistant",
            "content": "O prazo de rescisão é de 30 dias..."
        }
    ]
}
```

### Resposta

```json
{
    "resposta": "A multa por descumprimento é de 10% do valor total...",
    "fontes": [
        {
            "texto": "A multa rescisória corresponde a 10%...",
            "fonte": "contrato.pdf",
            "pagina": 7,
            "score": 0.94
        }
    ],
    "tokens_usados": 287,
    "latencia_ms": 1340,
    "cache_hit": false
}
```

---

## Streaming — resposta em tempo real

Para melhorar a experiência, o chatbot pode usar o endpoint `/chat/stream`, que envia a resposta token a token conforme a LLM gera, igual ao comportamento do ChatGPT.

```
Usuário envia a pergunta
    ↓
Sistema começa a responder imediatamente:
"O pra..." → "...zo de..." → "...rescisão..." → "...é de 30 dias."
```

Isso reduz a **percepção** de latência — o usuário vê a resposta chegando em vez de esperar em tela branca.

O streaming usa o protocolo SSE (*Server-Sent Events*):

```
POST /chat/stream

→ data: {"token": "O"}
→ data: {"token": " prazo"}
→ data: {"token": " de"}
→ data: {"token": " rescisão"}
→ data: {"token": " é"}
→ data: {"token": " de"}
→ data: {"token": " 30"}
→ data: {"token": " dias."}
→ data: {"fontes": [...], "tokens_usados": 287}
→ data: [DONE]
```

---

## Bases heterogêneas — o caso de validação do projeto

O documento oficial prevê validar o chatbot com **bases heterogêneas** — dados de diferentes formatos e domínios misturados na mesma base.

Um exemplo de configuração de validação:

```python
SOURCES = {
    "contratos": {
        "type": "pdf",
        "path": "./dados/contratos/"
    },
    "banco_processos": {
        "type": "postgresql",
        "query": "SELECT numero, ementa, texto FROM processos"
    },
    "manuais_tecnicos": {
        "type": "pdf",
        "path": "./dados/manuais/"
    }
}
```

Tudo vai para a mesma base vetorial, com metadados naturais (fonte, tipo, data). O chatbot faz perguntas que cruzam esses dados:

```
"Qual processo cita a cláusula de rescisão do contrato X?"
→ resposta envolve dados do banco SQL + dados do PDF
→ a busca híbrida atravessa tudo sem distinção
```

Esse cruzamento é exatamente o que valida o framework como genérico — ele não precisa saber de antemão que tipos de dados estão lá.

---

## O que medir no chatbot

O chatbot não é só demonstração — é o ambiente de coleta das métricas que o projeto precisa entregar.

### Métricas de desempenho

```
Latência de resposta:
  p50 (mediana)          → tempo típico
  p95                    → tempo para 95% das queries
  p99                    → pior caso comum

Throughput:
  queries por segundo    → capacidade do sistema
```

### Métricas de qualidade (RAGAS)

Para cada sessão de teste, o avaliador registra as queries feitas e as respostas esperadas, e roda o benchmark:

```bash
rag benchmark \
  --query "qual o prazo de rescisão?" \
  --esperado "contrato.pdf:3" \
  --estrategias bm25,dense,hybrid \
  --ragas
```

O resultado compara o BuscaAI contra os dois baselines que o documento do projeto pede:

```
Comparação com busca convencional (BM25 puro):
→ melhoria de X% no recall
→ melhoria de Y% no RAGAS score

Comparação com fine-tuning:
→ custo de atualização: BuscaAI = só reingerir | fine-tuning = retreinar
→ acurácia em dados novos: BuscaAI mantém | fine-tuning piora
```

### Mitigação de alucinação

O chatbot permite observar diretamente se o RAG está reduzindo alucinações. Com a métrica **Faithfulness** do RAGAS, o avaliador mede quantas afirmações da resposta têm suporte real nos documentos recuperados. Quanto mais próximo de 1.0, menos o sistema está inventando.

---

## Arquitetura do chatbot

O chatbot é uma aplicação separada — vive no diretório `frontend/` do projeto, com sua própria stack, e consome a API do BuscaAI:

```
[React + Tailwind CSS + Vite]
         ↓
    POST /chat ou /chat/stream
         ↓
    BuscaAI API (FastAPI)
         ↓
    LangGraph → Qdrant → LLM
```

A escolha por React + Tailwind + Vite reflete um padrão atual de stacks leves e produtivas para SPAs. O frontend sobe junto com o resto do ambiente via docker-compose (em `http://localhost:3000`).

A interface não precisa ser sofisticada para a POC — o que importa é que demonstre o fluxo e permita coletar as métricas. Os componentes mínimos:

- Campo de texto para a pergunta
- Área de exibição da resposta (com streaming via SSE)
- Lista das fontes usadas, com link para o documento original
- Histórico da conversa visível
- Botão para limpar o histórico
- Indicador de latência da última resposta (útil para validação)

---

## Relação com o restante do projeto

O chatbot fecha o ciclo do BuscaAI:

```
rag_settings.py   → configura o sistema
/ingest           → alimenta a base
/search           → busca para integrações
/chat             → chatbot de validação
/benchmark        → mede a qualidade
```

O chatbot usa o `/chat`, que por sua vez usa o grafo de busca completo (pré-filtragem + busca híbrida + reranker), com a camada extra de geração de resposta pela LLM e gerenciamento de histórico. É o uso mais completo do framework e, portanto, o melhor ambiente de validação.
