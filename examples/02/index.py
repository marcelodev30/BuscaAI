from langchain_text_splitters import (MarkdownHeaderTextSplitter,RecursiveCharacterTextSplitter)
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_litellm import LiteLLMEmbeddings
from langchain_core.documents import Document


import os

os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["DOCLING_DEVICE"] = "cpu"

from langchain_docling.loader import DoclingLoader

from dotenv import load_dotenv

load_dotenv()



embedder = LiteLLMEmbeddings(model="ollama/bge-m3",api_base="http://192.168.164:11434")



splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,       
    chunk_overlap=75,
    keep_separator=False,

)

loader = DoclingLoader(file_path="02.pdf")
docs = loader.load()


for text in docs:
    print("------------ ----------- ")
    print(text)
    print("-------------------------------------")
    print(text.metadata)
    print("------------ ----------- ")
