from langchain_elasticsearch import ElasticsearchStore, DenseVectorStrategy,BM25Strategy
from langchain_ollama import OllamaEmbeddings
from langchain_litellm import ChatLiteLLM

from system_prompt import formatar, prompt 
import logging
import os
from dotenv import load_dotenv

logging.getLogger("LiteLLM").setLevel(logging.ERROR)
load_dotenv() 

embeddings = OllamaEmbeddings(
    model="bge-m3",
    base_url=os.getenv("OLLAMA_URL"), num_ctx=512
)

elastic = ElasticsearchStore(
    index_name="rag-v3",
    embedding=embeddings,
    es_url=os.getenv("ES_URL"),
    es_user=os.getenv("ES_USER"),
    es_password=os.getenv("ES_PASSWORD"),
    strategy=DenseVectorStrategy(),
)

llm = ChatLiteLLM(
    model="gemini/gemini-3.6-flash",
    temperature=0,
    max_tokens=2000,
)

def buscar(question: str, k: int = 10):
    retriever = elastic.as_retriever(search_kwargs={"k": k})
    return retriever.invoke(question)

def gerar(question: str, docs) -> str:

    augmented = prompt.invoke({
        "context": formatar(docs),
        "question": question})
    
   # Generation = llm.invoke(augmented).content
    return augmented.to_string()


