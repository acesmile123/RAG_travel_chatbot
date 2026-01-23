import os
from dotenv import load_dotenv

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION_NAME")
EMBED_MODEL = os.getenv("EMBED_MODEL")
RERANK_MODEL = os.getenv("RERANK_MODEL")
HF_TOKEN = os.getenv("HF_TOKEN")

# Ollama Configuration (Private Server)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "60.0"))

# Two-Model Architecture:
# Model A: Lightweight reasoning for RAG internal logic (query rewriting, routing)
# Model B: Fine-tuned model for final answer generation
RETRIEVER_MODEL = os.getenv("RETRIEVER_MODEL", "qwen3:1.7b")
GENERATOR_MODEL = os.getenv("GENERATOR_MODEL", "qwen3finetune:latest")

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/travel_chatbot")




