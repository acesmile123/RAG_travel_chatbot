from __future__ import annotations
from typing import Optional, Dict, List, Tuple, Any
import json, re
import httpx

from qdrant_client.http import models as qdm
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, EMBED_MODEL, RERANK_MODEL, OLLAMA_BASE_URL, RETRIEVER_MODEL, OLLAMA_TIMEOUT


# ========================== LLM CLIENT CONFIGURATION ==========================
# Ollama RETRIEVER Model (Model A) for internal logic tasks:
# - Query Rewriting
# - Intent Routing
# - Document Relevance Checking
# Uses lightweight model for fast reasoning
# ===============================================================================

# ========================== INIT MODELS ==========================

LLM_MODEL = RETRIEVER_MODEL  # Use configured retriever model (qwen3:1.7b)

client_qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

embeddings = HuggingFaceEmbeddings(
    model_name=EMBED_MODEL,
    encode_kwargs={"normalize_embeddings": True},
)

for field in ["province", "type"]:
    client_qdrant.create_payload_index(
        collection_name=COLLECTION_NAME,
        field_name=field,
        field_schema=qdm.PayloadSchemaType.KEYWORD,
    )


vectorstore = QdrantVectorStore(
    client=client_qdrant,
    collection_name=COLLECTION_NAME,
    embedding=embeddings,
    content_payload_key="content",
    metadata_payload_key=None,
)

reranker = CrossEncoder(RERANK_MODEL)


# ====================== PRE-RETRIEVAL ======================

def chat_llm(messages, model=LLM_MODEL):
    """Call Ollama API for chat completion"""
    try:
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.0,
            }
        }
        
        with httpx.Client(timeout=OLLAMA_TIMEOUT) as client:
            response = client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            return result["message"]["content"].strip()
            
    except httpx.TimeoutException:
        raise Exception(f"Ollama request timeout after {OLLAMA_TIMEOUT}s")
    except httpx.RequestError as e:
        raise Exception(f"Cannot connect to Ollama at {OLLAMA_BASE_URL}: {e}")
    except Exception as e:
        raise Exception(f"Ollama API error: {e}")


def rewrite_query_llm(query: str) -> str:
    """
    Rewrite query bằng LLM để tạo truy vấn tìm kiếm tối ưu.
    Ví dụ: "ăn gì Đà Nẵng?" → "ẩm thực, món ăn, nhà hàng tại Đà Nẵng"
    """
    if len(query.split()) > 4:
        return query
    
    prompt = f"""
Bạn là trợ lý cho hệ thống RAG du lịch Việt Nam.

YÊU CẦU:
- Viết lại truy vấn để tìm kiếm ngữ nghĩa
- GIỮ NGUYÊN TIẾNG VIỆT
- KHÔNG dịch sang tiếng Anh
- Chỉ trả về câu truy vấn đã viết lại

Truy vấn gốc : "{query}"

"""
    return chat_llm([
        {"role": "user", "content": prompt}
    ])



def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        return json.loads(m.group(0))

   
    return {"province": None, "type": None}

def route_query_llm(query: str) -> Dict:
    """
    Định tuyến dựa trên LLM:

    - Phát hiện tỉnh/thành phố

    - Phát hiện loại nội dung

    - Tạo bộ lọc Qdrant
    """

    prompt = f"""
Bạn là bộ phân loại intent cho chatbot du lịch Việt Nam.

YÊU CẦU:
- Trả về JSON
- KHÔNG dùng tiếng Anh ngoài các giá trị enum
- KHÔNG giải thích

Schema:
{{"province": "da_nang|phu_quoc|nha_trang|null",
  "type": "destination|food|transportation|pricing|schedule|general|null"}}

Câu truy vấn: "{query}"

"""

    text = chat_llm([
        {"role": "user", "content": prompt}
    ])
    
    data = _extract_json(text)

    must_clauses = []
    if data.get("province"):
        must_clauses.append({
            "key": "province",
            "match": {"value": data["province"]},
        })
    if data.get("type"):
        must_clauses.append({
            "key": "type",
            "match": {"value": data["type"]},
        })

    qdrant_filter = {"must": must_clauses} if must_clauses else None

    return {
        "province": data.get("province"),
        "type": data.get("type"),
        "filter": qdrant_filter,
    }


# ====================== RETRIEVER (MMR) ======================

def retrieve_mmr(query: str, k=10, fetch_k=40, qdrant_filter=None):
    docs = vectorstore.max_marginal_relevance_search(
        query=query,
        k=k,
        fetch_k=fetch_k,
        filter=qdrant_filter,
    )
    return docs


# ====================== POST-RETRIEVAL ======================

def rerank_bge(query: str, docs, top_n=5):
    if not docs:
        return []

    pairs = [[query, d.page_content] for d in docs]
    scores = reranker.predict(pairs)

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
    reranked_docs = [doc for doc, _ in ranked[:top_n]]
    return reranked_docs


# ====================== RAG ANSWER ======================

def build_context(docs, max_chars=3000):
    result, total = [], 0
    for i, d in enumerate(docs, 1):
        text = d.page_content
        if total + len(text) > max_chars:
            break
        result.append(f"[CHUNK {i}]\n{text}")
        total += len(text)
    return "\n\n".join(result)




# ====================== FULL PIPELINE ======================
    
def rag_pipeline(query: str):
    print("User query:", query)

    # 1. Rewrite
    rewritten = rewrite_query_llm(query)
    print("Rewritten:", rewritten)

    # 2. Routing
    route_info = route_query_llm(rewritten)
    print("Routing:", route_info)

    # 3. Retrieve (MMR)
    docs = retrieve_mmr(
        query=rewritten,
        k=25,
        fetch_k=50,
        qdrant_filter=route_info["filter"],
    )
    print("Retrieved:", len(docs))

    # 4. Re-rank (BGE)
    reranked = rerank_bge(rewritten, docs, top_n=8)
    print("Reranked:", len(reranked))

    # 5. Build context
    ctx = build_context(reranked)

    return ctx



if __name__ == "__main__":
    print("Điền query: ")
    n= input().strip()
    res = rag_pipeline(n)
    print("\n==================== FINAL ANSWER ====================\n")
    print(res)
