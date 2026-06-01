from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import (MarkdownHeaderTextSplitter,RecursiveCharacterTextSplitter)
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

from langchain_community.retrievers import BM25Retriever 
from langchain_classic.retrievers import EnsembleRetriever
from langchain_community.document_loaders import PyMuPDFLoader
import unicodedata

import re
import json
import fitz  # PyMuPDF
from langchain_core.documents import Document

load_dotenv()


def limpar_texto(texto: str) -> str:
    # 1. Normaliza unicode (acentos, aspas curvas, traços especiais...)
    texto = unicodedata.normalize("NFKC", texto)

    # 2. Junta palavras quebradas por hífen no fim da linha: "pré-\nprocessamento" -> "préprocessamento"
    texto = re.sub(r"-\n", "", texto)

    # 3. Remove quebras de linha simples que cortam frases (mantém parágrafos)
    #    Une linha que NÃO termina em pontuação com a próxima
    texto = re.sub(r"(?<![.!?:;])\n(?!\n)", " ", texto)

    # 4. Colapsa espaços e tabs múltiplos em um só
    texto = re.sub(r"[ \t]+", " ", texto)

    # 5. Reduz três ou mais quebras de linha para no máximo duas (separação de parágrafo)
    texto = re.sub(r"\n{3,}", "\n\n", texto)

    # 6. Remove caracteres de controle invisíveis
    texto = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", texto)

    return texto.strip()

docs = fitz.open("02.pdf")
documents = []
for i, page in enumerate(docs):
    texto = page.get_text("text")
    texto = limpar_texto(texto)              
    if not texto:                            
        continue
    documents.append(
        Document(page_content=texto, metadata={"source": "02.pdf", "page": i})
    )
docs.close()

print(documents[1])



loader = PyMuPDFLoader("02.pdf")
docs = loader.load()

print(docs[0])


splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,       
    chunk_overlap=75,
    keep_separator=False,
)


#chunks = splitter.split_documents(docs)

#print(chunks)


#print(len(chunks[10].page_content))








''''
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001",output_dimensionality=1536)


vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db",   
    collection_name="rag",  
)
'''



''''
vectorstore = Chroma(
    embedding_function=embeddings,
    persist_directory="./chroma_db",   
    collection_name="rag",  
)


for i, chunk in enumerate(chunks[:10]):
    print(f"\n--- Chunk {i} ({len(chunk.page_content)} chars) ---")
    print(chunk.page_content)

results = vectorstore.similarity_search(
    "o que é RAG?"
)

for doc in results:
    print(doc.page_content)
    print("\n=================\n")



bm25_retriever = BM25Retriever.from_documents(chunks)
bm25_retriever.k = 4

# Retriever vetorial (Chroma)
chroma_retriever = vectorstore.as_retriever(
    search_kwargs={"k": 4}
)

# Combinando os dois
hybrid_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, chroma_retriever],
    weights=[0.4, 0.6],  # 40% BM25 + 60% semântico
)

docs = hybrid_retriever.invoke("três modelos de embeddings")
for doc in docs:
    print(doc.page_content)'''




def carregar_chunks(caminho_jsonl):
    chunks = []
    with open(caminho_jsonl, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                chunks.append(json.loads(linha))
    return chunks






