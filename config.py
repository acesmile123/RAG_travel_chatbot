import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
EMBED_MODEL = os.getenv("EMBED_MODEL")
RERANK_MODEL = os.getenv("RERANK_MODEL")
HF_TOKEN = os.getenv("HF_TOKEN")




