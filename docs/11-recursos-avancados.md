# Recursos Avançados

Este arquivo explica três recursos que aparecem no framework mas que não são necessários para começar: query expansion, o modelo SPLADE para embeddings esparsos, e multi-tenant.

---

## Query Expansion

### O problema que ela resolve

Queries curtas ou vagas encontram menos resultados relevantes. O embedding de uma query com poucas palavras representa um espaço semântico estreito — pode não cobrir todas as formas como o assunto aparece na base.

```
Query original: "rescisão"
→ encontra chunks que falam especificamente em "rescisão"
→ pode perder chunks sobre "encerramento de contrato", "término", "distrato"
```

### O que é query expansion

É uma etapa **antes** da busca onde uma LLM reformula ou expande a query original, gerando versões mais ricas ou alternativas.

```
Query original:   "rescisão"
                      ↓
              LLM expande
                      ↓
Query expandida:  "rescisão contratual, encerramento de contrato,
                  distrato, término de acordo, resilição"
```

A busca então usa a query expandida e encontra mais documentos relevantes — melhorando o **recall**.

### Como entra no fluxo

```
query chega
      ↓
[query expansion?] ← condicional (se habilitado no settings)
      ↓ sim
[LLM reformula a query]
      ↓
[pré-filtragem léxica com query expandida]
      ↓
[busca híbrida]
      ↓
...
```

### O trade-off

```
Vantagem:  melhora o recall (encontra mais coisas relevantes)
Custo:     adiciona uma chamada de LLM por query
           adiciona latência (~200-500ms dependendo do modelo)
```

Por isso o query expansion é **desligado por padrão**. Vale ligar quando:

- A base tem vocabulário variado para o mesmo conceito.
- Os usuários tendem a fazer queries curtas e vagas.
- Recall é mais crítico que latência para o caso de uso.

Para minimizar o custo, usa-se um modelo leve (Groq com Llama, por exemplo) em vez de um modelo caro.

### Configuração

```python
LLM_FEATURES = {
    "query_expansion": {
        "enabled": False,          # desligado por padrão
        "provider": "groq",        # modelo barato, tarefa simples
        "model": "llama-3.1-8b-instant",
        "instrucao": """Expanda a query abaixo com sinônimos e termos relacionados.
                       Retorne só os termos, separados por vírgula.
                       Query: {query}"""
    }
}
```

---

## SPLADE e FastEmbed — embeddings esparsos de verdade

### Por que não usar BM25 puro para o embedding esparso

BM25 é um algoritmo baseado em frequência de termos — ele não aprende nada, só conta palavras e calcula pesos estáticos. Funciona bem, mas tem limitações: não entende morfologia, não generaliza para variações da mesma palavra.

**SPLADE** (*Sparse Lexical and Expansion Model*) é um modelo neural que gera embeddings esparsos, mas aprende como fazê-lo a partir de dados. Em vez de só contar a palavra "rescisão", ele pode aprender que "rescisão" e "distrato" merecem pesos parecidos no vetor esparso — combinando o melhor do léxico com um grau de semântica.

```
BM25 para "rescisão contratual":
→ {"rescisão": 0.8, "contratual": 0.6}
   (só as palavras que aparecem)

SPLADE para "rescisão contratual":
→ {"rescisão": 0.8, "contratual": 0.6, "distrato": 0.3, "término": 0.2}
   (inclui termos relacionados aprendidos)
```

### FastEmbed

FastEmbed é uma biblioteca do Qdrant para gerar embeddings de forma eficiente localmente, sem chamar API externa. Ela inclui modelos prontos para embeddings densos e esparsos, incluindo SPLADE.

```python
from fastembed import SparseTextEmbedding

modelo = SparseTextEmbedding("prithivida/Splade_PP_en_v1")
embedding = list(modelo.embed("rescisão contratual"))[0]
# retorna um SparseEmbedding com indices e values
```

Vantagens do FastEmbed:

```
Roda local               → sem custo de API, sem latência de rede
Otimizado para Qdrant    → formato de saída já compatível
Modelos leves            → funciona bem em CPU
```

### Como os dois embeddings ficam no Qdrant

O Qdrant suporta vetores múltiplos por ponto desde a versão 1.7 — você pode salvar o vetor denso e o esparso no mesmo registro:

```python
qdrant.upsert(
    collection_name="principal",
    points=[
        PointStruct(
            id=chunk_id,
            vector={
                "denso":   [0.23, 0.87, 0.12, ...],   # OpenAI, Cohere, etc
                "esparso": SparseVector(               # SPLADE via FastEmbed
                    indices=[102, 387, 512],
                    values=[0.8, 0.6, 0.4]
                )
            },
            payload=metadados
        )
    ]
)
```

Na busca híbrida, o Qdrant usa os dois vetores automaticamente e faz a fusão com RRF internamente.

### Resumo dos modelos de embedding esparso

| Modelo | Tipo | Custo | Qualidade | Indicado para |
|---|---|---|---|---|
| BM25 puro | algoritmo | zero | básica | bases simples, português |
| SPLADE | neural local | baixo (CPU) | boa | padrão do BuscaAI |
| Embedding esparso via API | neural API | médio | muito boa | quando qualidade é crítica |

O BuscaAI usa SPLADE via FastEmbed como padrão — bom equilíbrio entre qualidade e custo zero de API.

---

## Multi-tenant

### O que é multi-tenant

Multi-tenant é quando um mesmo sistema atende **múltiplos clientes** (tenants), com isolamento entre eles — cliente A não pode ver nem acessar os dados do cliente B.

```
Tenant A (empresa jurídica):
  → ingere contratos, acórdãos, pareceres
  → suas queries só buscam nesses dados

Tenant B (empresa de saúde):
  → ingere prontuários, protocolos, laudos
  → suas queries só buscam nesses dados
  → nunca acessa dados do Tenant A
```

### Quando multi-tenant importa

Para a maioria dos usos do BuscaAI, multi-tenant não é necessário — é um único time/empresa usando o sistema. Mas se o BuscaAI for oferecido como serviço para múltiplos clientes diferentes (SaaS), o isolamento vira obrigação.

### Como o isolamento funciona no BuscaAI

A decisão tomada no projeto foi remover collections como conceito obrigatório — uma collection única com metadados resolve a maioria dos casos. Para multi-tenant, as collections voltam como mecanismo de isolamento:

```
Opção 1 — Uma collection por tenant (isolamento total):
  collection "tenant_a" → só dados do cliente A
  collection "tenant_b" → só dados do cliente B
  → mais seguro, mais simples de gerenciar
  → mais caro (índice separado por tenant)

Opção 2 — Collection única com filtro por tenant_id:
  tudo na collection "principal"
  cada chunk tem metadado: tenant_id = "empresa_juridica"
  busca sempre filtra: tenant_id = token.tenant_id
  → mais eficiente em espaço
  → exige que o filtro seja sempre aplicado (risco se esquecer)
```

O BuscaAI suporta ambas. A Opção 1 é mais segura para dados sensíveis.

### Como o tenant é identificado

O token JWT do usuário carrega o `tenant_id`. A API extrai esse ID automaticamente e aplica o isolamento:

```python
# o dev não precisa passar o tenant_id nas requests
# a API extrai do token e aplica o filtro automaticamente

POST /search
Authorization: Bearer eyJhbGc...   ← token contém tenant_id

# por baixo, a API faz:
tenant_id = token.claims["tenant_id"]
buscar(query=query, filtros={"tenant_id": tenant_id})
```

### Configuração

```python
MULTITENANCY = {
    "enabled": False,                  # desligado por padrão
    "isolation": "collection",         # "collection" ou "filter"
    "tenant_field": "tenant_id"        # nome do campo nos metadados
}
```

### Impacto no ciclo de vida dos dados

Com multi-tenant, ingestão e deleção passam a ter escopo por tenant:

```bash
# ingere só para o tenant do usuário logado
rag ingest --source ./docs/

# deleta só documentos do tenant do usuário logado
DELETE /documents/{id}

# admin pode operar em qualquer tenant
rag --tenant empresa_juridica ingest --source ./docs/
```
