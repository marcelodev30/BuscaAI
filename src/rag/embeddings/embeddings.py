from langchain_litellm import LiteLLMEmbeddings
from dotenv import load_dotenv
from typing import Optional
load_dotenv()

class LiteLLMEmbedder:
    def __init__(self, model_name: str,dimension:Optional[int]=1536,api_base:Optional[str]=None):
        self.model_name = model_name
        self.dimension = dimension
        self._embedder = LiteLLMEmbeddings(
            model=self.model_name,
            dimensions=self.dimension,
            api_base=api_base,
        )

    def get_embedder_instance(self) -> LiteLLMEmbeddings:
        return self._embedder

    def get_embedder_model_name(self) -> str:
        return self._embedder.model

    async def embedder_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embedder.aembed_documents(texts)

    async def embedder_query(self, query: str) -> list[float]:
        return await self._embedder.aembed_query(query)


#models/gemini-embedding-001
#gemini/gemini-2.0-flash
#ollama/bge-m3
#api_base="http://192.168.164:11434"
#"gemini/gemini-embedding-001"

def embeddings(text:str):
    from FlagEmbedding import FlagAutoModel
    model = FlagAutoModel.from_finetuned('BAAI/bge-m3', use_fp16=False)
    return model.encode([text], return_dense=True, return_sparse=True)

