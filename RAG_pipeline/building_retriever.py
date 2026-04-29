from __future__ import annotations
from typing import Optional, Dict, List, Any
import json, re
import unicodedata

from qdrant_client.http import models as qdm
from qdrant_client import QdrantClient
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse
from langchain_huggingface import HuggingFaceEmbeddings
from sentence_transformers import CrossEncoder
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, EMBED_MODEL, RERANK_MODEL, GROQ_API_KEY
from groq import Groq

LLM_MODEL = "llama-3.3-70b-versatile"

# ========================== INIT MODELS ==========================

client = Groq(api_key="GROQ_API_KEY")

client_qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
)

embeddings = HuggingFaceEmbeddings(
    model_name=EMBED_MODEL,
    encode_kwargs={"normalize_embeddings": True},
)

sparse_embeddings = FastEmbedSparse(model_name="Qdrant/bm25")

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
    sparse_embedding=sparse_embeddings,
    vector_name="dense",
    sparse_vector_name="sparse",
    content_payload_key="content",
    metadata_payload_key=None,
)


def get_provinces_from_qdrant(client, collection_name):
    provinces = set()
    points, _ = client.scroll(
        collection_name=collection_name,
        limit=1000,
        with_payload=True,
    )
    for p in points:
        payload = p.payload
        if payload and "province" in payload:
            provinces.add(payload["province"])
    return list(provinces)


reranker = CrossEncoder(RERANK_MODEL)
PROVINCES = get_provinces_from_qdrant(client_qdrant, COLLECTION_NAME)
print("Loaded provinces:", PROVINCES)


# ====================== PRE-RETRIEVAL ======================

def chat_llm(messages: List[Dict], model=LLM_MODEL) -> str:
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.1,
    )
    return resp.choices[0].message.content.strip()


def condense_question(query: str, chat_history: List[Dict]) -> str:
    """
    Nếu có lịch sử hội thoại, dùng LLM để viết lại câu hỏi thành
    câu độc lập (standalone), không phụ thuộc ngữ cảnh trước.
    Ví dụ: "còn ăn gì nữa không?" → "ăn gì ở Hà Nội ngoài phở?"
    """
    if not chat_history:
        return query

    # Chỉ lấy 6 lượt gần nhất để tránh context quá dài
    recent = chat_history[-6:]
    history_text = "\n".join([
        f"{'User' if m['role'] == 'user' else 'Bot'}: {m['content'][:200]}"
        for m in recent
    ])

    prompt = f"""Dựa vào lịch sử hội thoại bên dưới, hãy viết lại câu hỏi cuối thành câu hỏi độc lập, đầy đủ nghĩa mà không cần đọc lịch sử.

Lịch sử:
{history_text}

Câu hỏi hiện tại: "{query}"

Yêu cầu:
- Nếu câu hỏi đã rõ ràng, giữ nguyên
- Nếu câu hỏi tham chiếu đến thứ đã đề cập trước (ở đó, nơi đó, còn gì nữa...), hãy bổ sung đầy đủ
- Chỉ trả về câu hỏi đã viết lại, không giải thích
- Giữ nguyên tiếng Việt"""

    return chat_llm([{"role": "user", "content": prompt}])


def normalize(text: str) -> str:
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text


def detect_province(query: str, provinces: List[str]) -> Optional[str]:
    q = normalize(query)
    sorted_provinces = sorted(provinces, key=lambda p: len(p), reverse=True)
    for p in sorted_provinces:
        name = normalize(p.replace("_", " "))
        pattern = r'(?<![a-z])' + re.escape(name) + r'(?![a-z])'
        if re.search(pattern, q):
            return p
    return None


def _extract_json(text: str) -> Dict[str, Any]:
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
    matches = re.findall(r"\{[^{}]*\}", text)
    for m in matches:
        try:
            return json.loads(m)
        except:
            continue
    return {"type": None}


def route_query_llm(query: str) -> Dict:
    province = detect_province(query, PROVINCES)

    prompt = f"""Bạn là bộ phân loại intent cho chatbot du lịch Việt Nam.

YÊU CẦU:
- Trả về JSON
- KHÔNG dùng tiếng Anh ngoài các giá trị enum
- KHÔNG giải thích

{{"type": "destination|food|transportation|accommodation|pricing|schedule|general|null"}}

Câu truy vấn: "{query}"
"""
    text = chat_llm([{"role": "user", "content": prompt}])
    data = _extract_json(text)
    detected_type = data.get("type")

    must_clauses   = []
    should_clauses = []

    if province:
        must_clauses.append(
            qdm.FieldCondition(key="province", match=qdm.MatchValue(value=province))
        )

    if detected_type and detected_type not in ("null", "general", None):
        should_clauses.append(
            qdm.FieldCondition(key="type", match=qdm.MatchValue(value=detected_type))
        )
        should_clauses.append(
            qdm.FieldCondition(key="type", match=qdm.MatchValue(value="general"))
        )

    qdrant_filter = None
    if must_clauses or should_clauses:
        qdrant_filter = qdm.Filter(
            must=must_clauses   if must_clauses   else None,
            should=should_clauses if should_clauses else None,
        )

    return {
        "province": province,
        "type":     detected_type,
        "filter":   qdrant_filter,
    }


# ====================== RETRIEVAL ======================

def retrieve_mmr(query: str, k=25, fetch_k=60, qdrant_filter=None):
    docs = vectorstore.max_marginal_relevance_search(
        query=query,
        k=k,
        fetch_k=fetch_k,
        filter=qdrant_filter,
    )
    # Fallback nếu filter quá chặt
    if len(docs) < 3 and qdrant_filter is not None:
        print("⚠️  Fallback no-filter")
        docs = vectorstore.max_marginal_relevance_search(
            query=query, k=k, fetch_k=fetch_k
        )
    return docs


# ====================== POST-RETRIEVAL ======================

def rerank_bge(query: str, docs, top_n=7):
    if not docs:
        return []
    pairs  = [[query, d.page_content] for d in docs]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked[:top_n]]


def build_context(docs, max_chars=4500) -> str:
    result, total = [], 0
    for i, d in enumerate(docs, 1):
        text = d.page_content
        if total + len(text) > max_chars:
            break
        result.append(f"[CHUNK {i}]\n{text}")
        total += len(text)
    return "\n\n".join(result)


# ====================== GENERATION ======================

def generate_answer(
    query: str,
    context: str,
    chat_history: List[Dict],
):
    """
    Sinh câu trả lời có stream.
    chat_history: list các dict {"role": "user"|"assistant", "content": "..."}
    """
    system_prompt = (
        "Bạn là trợ lý du lịch chuyên nghiệp, am hiểu sâu sắc về du lịch Việt Nam.\n"
        "Hãy trả lời một cách thân thiện, chính xác, chi tiết và nhiệt tình. "
        "Sử dụng emoji phù hợp 🏖️🍲☕🏞️.\n"
        "Khi người dùng hỏi tiếp theo dựa trên cuộc trò chuyện, hãy nhớ ngữ cảnh trước."
    )

    rag_prompt = f"""Dưới đây là tài liệu tham khảo:

<context>
{context}
</context>

QUY TẮC:
1. TUYỆT ĐỐI CHỈ DÙNG thông tin trong <context>. KHÔNG bịa thêm.
2. Liệt kê rõ ràng từng ý, có địa chỉ/giá/giờ nếu context có.
3. Nếu <context> không đủ thông tin, hãy nói: "Tôi chưa có đủ thông tin về điều này, bạn có thể hỏi cụ thể hơn không?"

Câu hỏi: {query}"""

    # Xây dựng messages: system + lịch sử (tối đa 6 lượt) + câu hỏi mới
    messages = [{"role": "system", "content": system_prompt}]

    # Thêm lịch sử hội thoại (chỉ giữ 6 lượt gần nhất tránh vượt context window)
    for msg in chat_history[-6:]:
        messages.append({"role": msg["role"], "content": msg["content"][:600]})

    # Câu hỏi hiện tại kèm context
    messages.append({"role": "user", "content": rag_prompt})

    stream = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0.15,
        stream=True,
    )

    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta


# ====================== FULL PIPELINE ======================

def rag_pipeline(query: str, chat_history: List[Dict] = None):
    """
    Args:
        query:        Câu hỏi hiện tại của user
        chat_history: List [{"role": "user"|"assistant", "content": "..."}]
                      Truyền vào từ session_state của Streamlit
    Yields:
        str — từng chunk text để stream ra UI
    """
    if chat_history is None:
        chat_history = []

    print(f"\n👤 User: {query}")

    # 1. Condense: viết lại câu hỏi thành standalone nếu có lịch sử
    standalone = condense_question(query, chat_history)
    print(f"📝 Standalone: {standalone}")

    # 2. Routing
    route_info = route_query_llm(standalone)
    print(f"🗺️  Route: province={route_info['province']} | type={route_info['type']}")

    # 3. Retrieve
    docs = retrieve_mmr(
        query=standalone,
        k=25,
        fetch_k=60,
        qdrant_filter=route_info["filter"],
    )
    print(f"📚 Retrieved: {len(docs)}")

    # 4. Rerank
    reranked = rerank_bge(standalone, docs, top_n=7)
    print(f"🔝 Reranked: {len(reranked)}")

    # 5. Build context + generate
    ctx = build_context(reranked)
    yield from generate_answer(query, ctx, chat_history)


# ====================== CLI ======================

if __name__ == "__main__":
    print("🤖 Travel Chatbot ready! (gõ 'exit' để thoát)\n")

    history: List[Dict] = []

    while True:
        query = input("👤 Bạn: ").strip()
        if query.lower() in ["exit", "quit", "q"]:
            print("👋 Tạm biệt!")
            break

        print("🤖 Chatbot: ", end="", flush=True)
        answer_chunks = []

        for chunk in rag_pipeline(query, chat_history=history):
            print(chunk, end="", flush=True)
            answer_chunks.append(chunk) 

        full_answer = "".join(answer_chunks)
        print("\n" + "-" * 50)

        # Cập nhật lịch sử
        history.append({"role": "user",      "content": query})
        history.append({"role": "assistant", "content": full_answer})