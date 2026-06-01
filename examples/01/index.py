from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain_chroma import Chroma

from langchain_experimental.text_splitter import SemanticChunker

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter
)


load_dotenv()
url="/Users/marceloalves/Documents/developer/BuscaAI/docs/24-termos-tecnico-rag.md"

embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001",output_dimensionality=1536)

#embedding = embeddings.embed_query("marcelo")
#print(embedding)

'''
vector_store = Chroma(
    collection_name="example_collection",
    embedding_function=embeddings,
    persist_directory="./chroma_langchain_db",  
)


results = vector_store.similarity_search(
    "quem gerencia containers?"
)

'''

'''
for r in results:
    print(r.page_content)
    print(r.metadata)


llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash",temperature=0)
response = llm.invoke([ HumanMessage(content="Olá")])
print(response.content)

'''

'''
loader = TextLoader(
    url,
    encoding="utf-8"
)

#documents = loader.load()



splitter = SemanticChunker(
    embeddings
)
chunks = splitter.create_documents([markdown_text])

# mostrar resultado
for i, chunk in enumerate(chunks):
    print(f"\n--- CHUNK {i} ---")
    print(chunk.page_content)'''




