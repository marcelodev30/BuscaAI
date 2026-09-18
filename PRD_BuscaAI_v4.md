# PRD --- BuscaAI

**Versão:** 4.0\
**Produto:** BuscaAI\
**Slogan:** Transforme seus documentos em um assistente de IA para o seu
próprio site.

## 1. Visão do produto

O BuscaAI é uma plataforma para transformar documentos de uma empresa em
um assistente de IA que pode ser publicado diretamente no site da
empresa.

A proposta é semelhante ao conceito de um NotebookLM, mas com uma
diferença central: o conhecimento não fica restrito à plataforma. O
usuário cria um notebook, adiciona seus documentos, configura o
comportamento do assistente e publica um chat no próprio site.

O assistente responde perguntas exclusivamente com base no conteúdo
disponível no notebook. Quando não encontra informação suficiente, pode
encaminhar o visitante para o WhatsApp da empresa.

## 2. Problema

Pequenas e médias empresas possuem informações espalhadas em documentos,
manuais, catálogos, regulamentos, políticas e outros arquivos. Muitas
vezes, o cliente precisa entrar em contato com a empresa para obter
informações que já estão nesses documentos.

O BuscaAI pretende transformar esse conteúdo em uma interface de
consulta simples, acessível diretamente pelo site da empresa.

## 3. Público-alvo

O MVP é direcionado principalmente a pequenos e médios negócios, como:

-   Farmácias
-   Escolas
-   Clínicas
-   Escritórios de advocacia
-   Lojas
-   Prestadores de serviços

### Persona 1 --- Cliente da empresa

Pessoa que acessa o site e utiliza o chat para tirar dúvidas.

### Persona 2 --- Proprietário ou responsável pelo negócio

Pessoa que cria o notebook, envia os PDFs, configura o assistente e
publica o chat no site.

### Persona 3 --- Operador BuscaAI

Responsável pelo acompanhamento operacional da plataforma, métricas,
custos, qualidade e saúde do sistema.

## 4. Objetivos do MVP

O MVP deve permitir:

1.  Autenticação com Google.
2.  Criação e gerenciamento de notebooks.
3.  Upload de arquivos PDF.
4.  Processamento e indexação dos documentos.
5.  Chat baseado no conteúdo do notebook.
6.  Configuração básica das instruções do assistente.
7.  Publicação de um widget de chat no site do cliente.
8.  Encaminhamento para WhatsApp quando necessário.
9.  Controle de limites de uso.
10. Acompanhamento operacional da plataforma.

## 5. Fora do escopo do MVP

Não fazem parte do MVP:

-   Crawl de sites.
-   Conectores externos.
-   Fontes SQL.
-   Formatos de arquivo além de PDF.
-   Compartilhamento de notebooks.
-   Organizações, equipes e múltiplos papéis.
-   Login com e-mail e senha.
-   Cobrança real.
-   Conversação multi-turn avançada.
-   Query Rewrite.
-   Modo protegido do widget com JWT/HMAC.
-   API pública.

## 6. Autenticação

O MVP utiliza autenticação exclusivamente por Google.

### Fluxo

1.  Usuário autentica com Google.
2.  Backend valida o ID Token.
3.  Usuário é localizado pelo `Google sub`.
4.  Caso não seja encontrado, o e-mail verificado é utilizado como
    segunda forma de resolução.
5.  Caso ainda não exista, o usuário é criado.
6.  Backend gera a sessão utilizando JWT.

### Endpoints

``` text
POST /v1/auth/google
```

A autenticação não depende do Elasticsearch ou do armazenamento de
documentos.

## 7. Notebook

O notebook representa uma base de conhecimento independente.

### Dados

Cada notebook possui:

-   ID
-   Nome
-   Ícone
-   Usuário proprietário
-   Data de criação
-   Data de atualização

### Regras

-   O nome é obrigatório.
-   O usuário pode possuir vários notebooks dentro do limite do plano.
-   Cada notebook possui seus próprios arquivos e conversas.
-   Os documentos de um notebook não podem ser utilizados por outro
    notebook.

### Operações

-   Criar notebook.
-   Listar notebooks.
-   Abrir notebook.
-   Renomear notebook.
-   Alterar ícone.
-   Excluir notebook.

A exclusão pode ocorrer de forma assíncrona.

## 8. Arquivos PDF

O MVP aceita somente PDF.

### Upload

O upload é realizado individualmente por arquivo.

Antes do processamento, o sistema deve validar:

1.  Autenticação.
2.  Propriedade do notebook.
3.  Bytes recebidos.
4.  Tamanho máximo.
5.  Magic bytes do PDF.
6.  Abertura válida do PDF.
7.  Proteção por senha.
8.  Quantidade de páginas.
9.  Checksum.
10. Quota disponível.

### Deduplicação

O sistema calcula um checksum do arquivo.

O mesmo PDF não pode ser duplicado dentro do mesmo notebook.

O mesmo arquivo pode existir em notebooks diferentes.

### Armazenamento

O PDF original não precisa ser mantido permanentemente.

O sistema gera e armazena uma representação estruturada do conteúdo para
o processamento.

## 9. Processamento dos documentos

O processamento possui três etapas principais:

``` text
PDF
 ↓
Extração
 ↓
Representação estruturada
 ↓
Chunking
 ↓
Embeddings
 ↓
Indexação
```

### Extração

O conteúdo do PDF é extraído e transformado em uma representação
estruturada.

### Chunking

O documento é dividido em chunks determinísticos.

Cada chunk deve possuir uma identificação estável.

### Indexação

Cada chunk recebe seu embedding e é enviado ao mecanismo de busca em
lotes.

O processamento deve permitir retomada em caso de falha.

### Estados do arquivo

``` text
pending
processing
ready
failed
empty
deleting
```

O banco mantém o estado do processamento para permitir acompanhamento,
diagnóstico e retomada.

O usuário recebe mensagens de erro simplificadas, enquanto detalhes
técnicos permanecem disponíveis para operação.

## 10. Chat do notebook

Cada notebook possui um chat normal.

O usuário pode criar várias conversas.

Ao abrir o notebook, a conversa mais recente pode ser apresentada por
padrão.

Cada pergunta é processada de forma independente no MVP.

O usuário pode avaliar a resposta com:

-   Positivo
-   Negativo

### Fluxo

``` text
Pergunta
 ↓
Retrieval
 ↓
Chunks relevantes
 ↓
Contexto
 ↓
Prompt
 ↓
LLM
 ↓
Resposta
```

O modelo deve responder exclusivamente com base no contexto recuperado.

Quando não houver informação suficiente, deve utilizar a mensagem:

> Não encontrei essa informação nos documentos disponíveis.

### Citações

A resposta pode possuir referências aos trechos utilizados.

O backend é responsável por montar as informações de arquivo, página e
seção a partir dos metadados armazenados.

O modelo não deve gerar diretamente nome de arquivo ou número de página.

As citações são exibidas no chat do notebook.

No widget público, as citações não são exibidas no MVP.

### Streaming

As respostas do chat devem ser transmitidas por streaming quando
possível.

## 11. Assistente

Cada notebook possui uma configuração de instrução adicional.

O usuário pode definir uma instrução de texto livre de até 250
caracteres.

Valor padrão:

``` text
Seja direto e objetivo.
```

A instrução do usuário é adicionada às regras fixas do sistema.

Ela não pode substituir as regras fundamentais de segurança e fidelidade
do BuscaAI.

Parâmetros como modelo, temperatura, chunking, embedding e reranking
permanecem ocultos no MVP.

## 12. Retrieval

O sistema possui um contrato único para Retrieval:

``` text
Entrada:
notebook + pergunta

Saída:
chunks relevantes
+ arquivo
+ página
+ seção
```

O filtro por usuário e notebook é obrigatório.

A estratégia interna de Retrieval pode ser alterada sem modificar o
contrato utilizado pelo chat.

O mecanismo pode utilizar estratégias híbridas, lexicais, vetoriais
 conforme a implementação.

## 13. Publicação do widget

Cada notebook pode possuir uma publicação do assistente.

O cliente recebe um código para incorporar o chat ao site.

O widget pode ser:

-   Flutuante.
-   Fixo.

### Configurações

-   Nome do assistente.
-   Cor.
-   Posição.
-   Mensagem de boas-vindas.
-   WhatsApp.
-   Domínios permitidos.

### Domínios

Uma lista de domínios pode restringir onde o widget funciona.

Uma lista vazia significa que nenhum domínio está autorizado.

As alterações de configuração devem entrar em vigor imediatamente.

Ao despublicar, o widget deixa de funcionar.

### Segurança do widget

O widget é público e anônimo.

O MVP utiliza:

-   Sessão curta.
-   Allowlist de origem.
-   Rate limit.
-   Quota mensal.

O modo protegido com JWT/HMAC fica fora do MVP.

Uma falha do widget nunca deve impedir o funcionamento do site do
cliente.

## 14. WhatsApp

Quando o assistente não conseguir responder adequadamente, o widget pode
oferecer encaminhamento para o WhatsApp da empresa.

O WhatsApp é uma funcionalidade do widget.

No chat interno do notebook, a mensagem de fallback continua sendo
apresentada normalmente.

## 15. Planos e quotas

O sistema possui limites de uso por plano.

### Plano Free

  Recurso                                Limite
  ----------------------------- ---------------
  Notebooks                                   3
  PDFs por notebook                          10
  Tamanho por PDF                         20 MB
  Páginas por PDF                           200
  Páginas por mês                           300
  Mensagens no widget por mês               200
  Publicações ativas                          1
  Indexação                       Compartilhada
  LLM                                 Econômico

### Plano Pro

  Recurso                           Limite
  ----------------------------- ----------
  Notebooks                             20
  PDFs por notebook                    100
  Tamanho por PDF                    50 MB
  Páginas por PDF                     1000
  Páginas por mês                     5000
  Mensagens no widget por mês         5000
  Publicações ativas                    10
  Indexação                       Dedicada
  LLM                               Melhor

O cliente não precisa visualizar o nome do modelo utilizado.

As quotas devem ser verificadas antes de iniciar operações que gerem
custo.

No processamento de documentos, o consumo deve ser contabilizado
conforme ocorre.

## 16. Operação

O dashboard operacional é destinado à equipe do BuscaAI.

Ele não funciona como sistema de suporte individual de arquivos.

### Negócio

-   Contas ativas.
-   Novas contas.
-   Notebooks publicados.
-   Funil de utilização.

### Qualidade

-   Taxa de respostas.
-   Taxa de fallback.
-   Relevância média.
-   Feedback positivo e negativo.

### Custos

-   Custo diário.
-   Custo mensal.
-   Custo por conta.
-   Custo médio por conversa.

### Saúde

-   Latência.
-   Tamanho da fila.
-   Idade do item mais antigo da fila.
-   Taxa de falhas.

### Auditoria

O sistema registra eventos operacionais, identidade do Retrieval e
metadados utilizados.

Não devem ser armazenados no log operacional:

-   Texto da pergunta.
-   Texto da resposta.
-   Tokens.
-   Conteúdo dos documentos.

## 17. Segurança

### Autorização

Todo recurso deve ser filtrado pelo usuário autenticado.

Um usuário não pode acessar notebook ou arquivo pertencente a outro
usuário.

### Índice

O filtro de usuário e notebook deve ser obrigatório na camada de
Retrieval.

A aplicação não deve depender da rota para lembrar de aplicar esse
filtro.

### Armazenamento

Os arquivos devem utilizar prefixo por usuário e URLs assinadas quando
necessário.

### Widget

O widget possui contexto de publicação próprio e não deve receber acesso
direto aos recursos internos da aplicação.

### Entrada

Dados recebidos pelo usuário devem ser normalizados e tratados como
dados, nunca como instruções confiáveis para o sistema.

### Erros

Cada erro deve possuir:

-   Código estável.
-   Mensagem em português.

O aplicativo cliente utiliza o código para determinar o comportamento.

Quando houver tentativa de acesso a um recurso de outro usuário, o
sistema deve responder como recurso inexistente.

## 18. API mínima do MVP

Para o protótipo Flutter, a API inicial pode permanecer pequena:

``` text
POST /v1/auth/google

POST /v1/notebooks
GET  /v1/notebooks
GET  /v1/notebooks/{notebook_id}

POST /v1/notebooks/{notebook_id}/files
GET  /v1/notebooks/{notebook_id}/files

POST /v1/notebooks/{notebook_id}/chat
```

O backend deve validar entradas HTTP utilizando Pydantic.

O processamento pesado dos PDFs pode ser executado em background no MVP,
sem introduzir inicialmente Celery, Redis ou outra infraestrutura de
filas.

## 19. Arquitetura inicial

Estrutura proposta:

``` text
src/
├── main.py
├── config.py
├── context.py
├── errors.py
│
├── api/
│   └── routes/
│       ├── auth.py
│       ├── notebooks.py
│       ├── files.py
│       └── chat.py
│
├── auth/
│   ├── schemas.py
│   ├── repository.py
│   └── google.py
│
├── notebooks/
│   ├── schemas.py
│   └── repository.py
│
├── files/
│   ├── schemas.py
│   ├── repository.py
│   └── validation.py
│
├── chat/
│   ├── schemas.py
│   └── prompt.py
│
├── rag/
│   ├── retrieval.py
│   ├── indexing.py
│   └── chunking.py
│
├── processing/
│   └── pipeline.py
│
├── llm/
│   └── provider.py
│
├── domain/
│   ├── quota.py
│   └── file_state.py
│
├── db/
│   ├── models.py
│   ├── session.py
│   └── migrations/
│
├── storage/
│   └── local.py
│
└── core/
    └── container.py
```

A estrutura deve permanecer simples. Não devem ser criadas camadas,
serviços, interfaces, factories ou abstrações sem necessidade concreta.

## 20. Dependency Injection e ciclo de vida

O projeto utiliza o sistema nativo de Dependency Injection do FastAPI
através de `Depends()` e `Security()`.

Dependências relacionadas ao HTTP, autenticação, autorização e recursos
da requisição devem utilizar o mecanismo do FastAPI.

Recursos pesados ou compartilhados devem possuir uma única instância por
processo quando forem projetados para reutilização.

Exemplos:

-   Elasticsearch client.
-   PostgreSQL engine/pool.
-   Embedding model.
-   LLM client.
-   Reranker.
-   Retriever.
-   Indexer.

A criação e destruição desses recursos deve ser centralizada no ciclo de
vida da aplicação utilizando `lifespan`.

As instâncias podem ser armazenadas em `app.state` ou em um Application
Container simples.

Exemplo conceitual:

``` text
lifespan
    ↓
cria recursos
    ↓
app.state / Container
    ↓
Depends()
    ↓
rota
```

As classes devem receber suas dependências pelo construtor quando
necessário:

``` python
class Indexer:
    def __init__(self, elasticsearch, embedder):
        self.elasticsearch = elasticsearch
        self.embedder = embedder
```

As classes não devem criar diretamente seus próprios clientes de
infraestrutura ou modelos compartilhados.

O código interno deve preferir dependências explícitas por parâmetros
normais de Python, evitando acoplamento desnecessário ao FastAPI.

Não utilizar `Depends()` como mecanismo geral de injeção para todas as
funções internas.

Não adicionar bibliotecas externas de Dependency Injection sem
necessidade concreta.

## 21. Persistência

O PostgreSQL será utilizado para dados transacionais e metadados da
aplicação.

Exemplos:

-   Usuários.
-   Notebooks.
-   Arquivos.
-   Estado do processamento.
-   Conversas.
-   Mensagens.
-   Configurações de publicação.
-   Uso e quotas.

O Elasticsearch ou outro mecanismo de Retrieval será utilizado para o
conteúdo indexado e recuperação dos chunks.

A camada de Retrieval deve ser a única responsável pelo acesso direto ao
índice de busca.

## 22. Princípios técnicos

### Pydantic

Toda entrada HTTP deve ser validada utilizando Pydantic.

### Rotas

As rotas devem ser pequenas e responsáveis principalmente por:

1.  Receber a requisição.
2.  Validar entrada.
3.  Resolver dependências.
4.  Chamar a lógica correspondente.
5.  Retornar a resposta.

### Repository

O acesso ao banco deve ser centralizado nos repositories
correspondentes.

### RAG

O pipeline deve manter separação entre:

``` text
Extraction
Chunking
Embedding
Indexing
Retrieval
Prompt
Generation
```

Os componentes de RAG devem possuir contratos simples e independentes da
API.

### Configuração

As implementações devem ser configuráveis sem alterar as regras
principais do sistema.

## 23. Regras de desenvolvimento

-   Preferir soluções simples.
-   Evitar abstrações prematuras.
-   Não criar camadas apenas por padrão arquitetural.
-   Não duplicar regras de negócio.
-   Validar todas as entradas externas.
-   Não instanciar recursos pesados por requisição.
-   Não instanciar modelos de embedding por arquivo ou por chunk.
-   Não acessar Elasticsearch diretamente a partir das rotas.
-   Sempre aplicar filtro de usuário e notebook no Retrieval.
-   Manter o processamento de documentos retomável.
-   Usar estados explícitos para o ciclo de vida dos arquivos.
-   Manter mensagens de erro estáveis.
-   Testar principalmente as regras de negócio e fluxos críticos.

## 24. Fluxo principal do produto

``` text
Usuário
   ↓
Login Google
   ↓
Dashboard
   ↓
Criar Notebook
   ↓
Upload PDF
   ↓
Validação
   ↓
Processamento
   ├── Extração
   ├── Chunking
   ├── Embedding
   └── Indexação
   ↓
Notebook pronto
   ↓
Chat
   ↓
Retrieval
   ↓
LLM
   ↓
Resposta + citações
```

Para publicação:

``` text
Notebook
   ↓
Configurar Assistente
   ↓
Publicar
   ↓
Código do Widget
   ↓
Site do cliente
   ↓
Visitante
   ↓
Chat
   ↓
Resposta baseada no notebook
   ↓
Sem informação
   ↓
WhatsApp
```

## 25. Critérios de sucesso do MVP

O MVP será considerado funcional quando um usuário conseguir:

1.  Entrar com Google.
2.  Criar um notebook.
3.  Enviar um PDF.
4.  Acompanhar o processamento.
5.  Ter o documento indexado.
6.  Fazer uma pergunta no notebook.
7.  Receber uma resposta baseada no documento.
8.  Visualizar as citações.
9.  Configurar a instrução do assistente.
10. Publicar o widget.
11. Inserir o widget em um site.
12. Fazer perguntas como visitante.
13. Ser encaminhado ao WhatsApp quando o sistema não encontrar
    informação.
14. Ter o uso limitado pelas quotas do plano.

## 26. Roadmap posterior

Após o MVP, podem ser considerados:

-   Crawl de sites.
-   Mais formatos de documentos.
-   Query Rewriting.
-   Multi-turn conversation.
-   Query Expansion.
-   HyDE.
-   Query Decomposition.
-   Modelos adicionais de Embedding.
-   Rerankers adicionais.
-   Modo protegido do widget.
-   API pública.
-   Compartilhamento de notebooks.
-   Equipes e organizações.
-   Billing real.
-   Integrações externas.
-   Índices dedicados avançados.
