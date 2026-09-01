import os
from typing import List

from dotenv import load_dotenv
from elasticsearch import Elasticsearch
from qdrant_client import QdrantClient, models
from sentence_transformers import SentenceTransformer

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_classic.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

from system_prompt import formatar, prompt

load_dotenv()

elastic_client = Elasticsearch(os.getenv("ES_URL"), request_timeout=120, retry_on_timeout=True,basic_auth=("elastic","dRWbd49Fg9QSMpdeg"))

qdrant_client = QdrantClient(url=os.getenv("QDRANT_URL"))

embedder_modelo = SentenceTransformer("BAAI/bge-m3", device="mps")
embedder_modelo.max_seq_length = 512


class PreFiltroRetriever(BaseRetriever):
    """ES corta o universo (BM25), Qdrant reordena por similaridade."""
    k: int = 30
    n_bm25: int = 200

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[Document]:
        busca_es = elastic_client.search(
            index="rag-v3",
            query={
                "bool": {
                    "must": [{"match": {"text": query}}],
                    "must_not": {
                        "terms": {
                            "metadata.headings.keyword": list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
                        }
                    },
                }
            },
            size=self.n_bm25,
            _source=False,
        )

        ids = [h["_id"] for h in busca_es["hits"]["hits"]]
        if not ids:
            return []

        vetor = embedder_modelo.encode(query, normalize_embeddings=True).tolist()

        pontos = qdrant_client.query_points(
            collection_name="rag-v3",
            query=vetor,
            query_filter=models.Filter(must=[models.HasIdCondition(has_id=ids)]),
            limit=self.k,
        ).points

        return [
            Document(page_content=p.payload["page_content"], metadata=p.payload["metadata"])
            for p in pontos
        ]


retriever = PreFiltroRetriever(k=30)



modelo = HuggingFaceCrossEncoder(
    model_name="BAAI/bge-reranker-v2-m3",
    model_kwargs={"device": "mps"},
)

Reranker = ContextualCompressionRetriever(
    base_compressor=CrossEncoderReranker(model=modelo, top_n=5),
    base_retriever=retriever,
)

pergunta = "O que é Engenharia de Software?"

docs= Reranker.invoke(pergunta)



print(formatar(docs))