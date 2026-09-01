from elasticsearch import Elasticsearch
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer
from system_prompt import formatar, prompt 

from langchain_core.documents import Document
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_core.runnables import RunnableLambda

import os
from dotenv import load_dotenv
load_dotenv() 

elastic_client = Elasticsearch("http://192.168.0.165:9200", request_timeout=120, retry_on_timeout=True,basic_auth=("elastic","dRWbd49Fg9QSMpdeg"))

embedder_modelo = SentenceTransformer("BAAI/bge-m3", device="mps")
embedder_modelo.max_seq_length = 512

qdrant_client = QdrantClient(url="http://192.168.0.165:6333")

def buscar_com_prefiltro(query: str,k:int):
    # Estagio 1: ES corta o universo
    busca_elasticsearch = elastic_client.search(
        index="rag-v3", 
        body={
        "query": {
            "bool": {
                "must": [{"match": {"text": query}}],
                "must_not": {"terms": {"metadata.headings": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")}},
            }
        },
        "size": 100,})
    
    ids = [h["_id"] for h in busca_elasticsearch["hits"]["hits"]]
    if not ids:
        return []

    vetor = embedder_modelo.encode(query,normalize_embeddings=True).tolist()
    
    # Estagio 2: Busca vetorial no qdrant com pre filtro de ids
    busca_vetoria = qdrant_client.query_points(
        collection_name="rag-v3",
        query=vetor,
        query_filter=models.Filter(
            must=[models.HasIdCondition(has_id=ids)]
        ),
        limit=k,
    ).points
    return [
        Document(page_content=h.payload["page_content"],
                 metadata=h.payload["metadata"]) for h in busca_vetoria]

retriever = RunnableLambda(lambda q: buscar_com_prefiltro(q, k=30))

pergunta = "O que é Engenharia de software ?"

modelo = HuggingFaceCrossEncoder(
    model_name="BAAI/bge-reranker-v2-m3",
    model_kwargs={"device": "mps"},
)
Reranker = ContextualCompressionRetriever(
    base_compressor=CrossEncoderReranker(model=modelo, top_n=5),
    base_retriever=retriever,
)

docs= Reranker.invoke(pergunta)

print(formatar(docs))