import json
import uuid
from tqdm import tqdm


from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, EMBED_MODEL



CHUNKS_FILE = "vinpearl_chunks_simple.json"  
VECTOR_SIZE = 768   # paraphrase-multilingual-mpnet-base-v2


# ========================== STEP 1: Load chunks =============================
def load_chunks(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)
    
# ========================== STEP 2: Init Qdrant =============================
def init_qdrant():
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        timeout=60
    )

    client.recreate_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    return client


# ========================== STEP 3: Load embedding model ====================s
def load_embedding_model():
    print("🔄 Loading embedding model...")
    return SentenceTransformer(EMBED_MODEL)


# ========================== STEP 4: Upsert to Qdrant ========================
def upload_to_qdrant(client, model, chunks):

    print("🚀 Bắt đầu upsert embeddings lên Qdrant Cloud...")

    batch = []

    for item in tqdm(chunks, desc="Encoding & batching"):

        # Encode nội dung
        vector = model.encode(item["content"], normalize_embeddings=True).tolist()

        # Create point
        batch.append(
            PointStruct(
                id=item["id"],
                vector=vector,
                payload={
                    "content": item["content"],
                    "province": item.get("province"),
                    "name": item.get("name"),
                    "section": item.get("section"),
                    "type": item.get("type"),
                    "source": item.get("source", "unknown"),
                    "tokens": item.get("tokens"),
                }
            )
        )

        # Upsert 100 items mỗi batch
        if len(batch) >= 100:
            client.upsert(collection_name=COLLECTION_NAME, points=batch)
            batch = []

    # Upsert batch cuối cùng
    if batch:
        client.upsert(collection_name=COLLECTION_NAME, points=batch)

    print(f"🎉 HOÀN TẤT! Đã upsert {len(chunks)} chunks lên Qdrant Cloud.")

# ========================== MAIN =============================
def main():

    print("\n========== LOAD CHUNKS ==========")
    chunks = load_chunks(CHUNKS_FILE)
    print(f"Loaded {len(chunks)} chunks!")

    print("\n========== INIT QDRANT ==========")
    client = init_qdrant()

    print("\n========== LOAD EMBEDDING MODEL ==========")
    model = load_embedding_model()

    print("\n========== UPSERT TO QDRANT ==========")
    upload_to_qdrant(client, model, chunks)



    
if __name__ == "__main__":
    main()