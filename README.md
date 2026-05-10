# Vietnam Tourism RAG Chatbot
<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-Frontend-61DAFB?logo=react&logoColor=black)
![Qdrant](https://img.shields.io/badge/Qdrant-VectorDB-DC244C?logo=qdrant&logoColor=white)
![Llama](https://img.shields.io/badge/Llama-3.3_70B-purple)

![SSE](https://img.shields.io/badge/Streaming-SSE-success)
![Hybrid Search](https://img.shields.io/badge/Hybrid_Search-Dense+Sparse-blue)
![CrossEncoder](https://img.shields.io/badge/Reranker-CrossEncoder-red)

</div>

<div align="left">

### Retrieval-Augmented Generation (RAG) Chatbot for Vietnamese Tourism Consultation

AI-powered tourism assistant built with **FastAPI**, **React**, **Qdrant**, and **Hybrid Retrieval**.

</div>

---

# 📌 Overview

**Vietnam Tourism RAG Chatbot** is an AI-powered tourism consultation system designed to answer travel-related questions about destinations, cuisine, accommodations, itineraries, and cultural attractions in Vietnam.

The project implements a complete **Retrieval-Augmented Generation (RAG)** pipeline including:

- 🌐 Web crawling & data collection
- ✂️ Semantic chunking
- 🧠 Dense + Sparse embeddings
- 🔎 Hybrid retrieval with Qdrant
- 📈 Reranking using Cross-Encoder
- 💬 Streaming chatbot responses (SSE)
- ⚡ FastAPI backend
- 🎨 React + Tailwind frontend

---

# ✨ Features

## 🤖 AI & RAG Features

- Hybrid Retrieval (**Dense + Sparse Search**)
- Context-aware question condensation
- Intent & province routing
- Cross-Encoder reranking
- Streaming LLM responses (Server-Sent Events)
- Multi-turn conversation support
- Session persistence
- Vietnamese tourism-focused knowledge base

---

## 🌐 Data Processing Pipeline

- HTML crawling
- Markdown conversion
- Semantic chunking
- Embedding generation
- Batch upsert to Qdrant

---

## ⚙️ Backend Features

- FastAPI REST API
- SSE token streaming
- Persistent chat sessions
- Async queue/thread bridge for stable streaming
- Modular RAG pipeline architecture

---

## 🎨 Frontend Features

- Vite + React frontend
- TailwindCSS UI
- Real-time streaming responses
- Session-aware conversations

---

# 🏗️ System Architecture

```text
User Query
    │
    ▼
Question Condensation
    │
    ▼
Intent / Province Routing
    │
    ▼
Hybrid Retrieval (Dense + Sparse)
    │
    ▼
Cross-Encoder Reranking
    │
    ▼
Context Building
    │
    ▼
LLM Generation (Streaming)
    │
    ▼
Final Response
```

---

# 🧠 RAG Pipeline

The retrieval pipeline is implemented in:

```bash
building_retriever.py
```

Main stages:

| Stage | Description |
|---|---|
| Query Condensation | Rewrites user query using chat history |
| Intent Routing | Detects travel intent & region |
| Hybrid Retrieval | Retrieves relevant chunks from Qdrant |
| Reranking | Uses CrossEncoder for relevance scoring |
| Context Building | Builds final prompt context |
| Generation | Streams answer from LLM |

---

# 🛠️ Tech Stack

| Category | Technology |
|---|---|
| Backend | FastAPI |
| Frontend | React + Vite + TailwindCSS |
| Vector Database | Qdrant |
| Embeddings | SentenceTransformers |
| Reranker | CrossEncoder |
| LLM | Llama 3.3 70B Versatile |
| Streaming | Server-Sent Events (SSE) |
| Data Processing | BeautifulSoup, Markdownify |
| Quantization Experiments | GPTQ, llm-compressor |

---

# 📂 Project Structure

```bash
.
├── main.py
├── building_retriever.py
├── vector_embeddings.py
├── data_collection_and_chunking.py
├── crawl_v2.py
├── config.py
├── requirements.txt
│
├── react_FE/
│   ├── src/
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
│
├── qdrant_local/
├── chat_sessions/
├── training_data_cleaned.jsonl
│
├── GPTQ_w8a8_Qwen3.ipynb
├── qlora_merged_ipynb.ipynb
└── QLoRA+Unsloth_Qwen3-14B.ipynb
```

---

# ⚡ Installation

## 1️⃣ Clone Repository

```bash
git clone https://github.com/acesmile123/RAG_travel_chatbot.git
cd RAG_travel_chatbot
```

---

## 2️⃣ Create Virtual Environment

### Windows

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Linux / MacOS

```bash
python -m venv .venv
source .venv/bin/activate
```

---

## 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

---

# 🔑 Environment Variables

Create a `.env` file in the root directory:

```env
QDRANT_URL=
QDRANT_API_KEY=
COLLECTION_NAME=

EMBED_MODEL=
RERANK_MODEL=

HF_TOKEN=
GROQ_API_KEY=
```

---

# 📚 Data Preparation Pipeline

## 1️⃣ Crawl & Chunk Data

```bash
python data_collection_and_chunking.py
```

or

```bash
python crawl_v2.py --txt urls.txt
```

---

## 2️⃣ Generate Embeddings & Upsert to Qdrant

```bash
python vector_embeddings.py
```

The script:

- Loads chunked JSON data
- Generates dense + sparse embeddings
- Performs batch upsert into Qdrant collection

---

# 🚀 Running the Backend

Start FastAPI server:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

---

# 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Health check |
| POST | `/sessions` | Create new session |
| GET | `/sessions` | Get all sessions |
| GET | `/sessions/{session_id}/messages` | Get session history |
| DELETE | `/sessions/{session_id}` | Delete session |
| POST | `/chat` | Chat streaming endpoint |

---

# 🌊 Streaming Response (SSE)

The chatbot streams responses using:

```text
text/event-stream
```

Example SSE payload:

```json
{
  "token": "Hello",
  "done": false
}
```

Final event:

```json
{
  "done": true,
  "session_id": "..."
}
```

---

# 🎨 Frontend Setup

Move to frontend folder:

```bash
cd react_FE
```

Install dependencies:

```bash
npm install
```

Run development server:

```bash
npm run dev
```

---

# 💻 Frontend Stack

| Technology | Purpose |
|---|---|
| React | UI framework |
| Vite | Build tool |
| TailwindCSS | Styling |
| SSE | Real-time token streaming |

---

# 🗄️ Qdrant Configuration

The project supports:

- Local Qdrant
- Docker Qdrant
- Managed Qdrant Cloud

Local sample metadata:

```bash
qdrant_local/
```

You still need to start a running Qdrant service and provide:

```env
QDRANT_URL
```

---

# 🧪 Research & Experimental Notebooks

## GPTQ Quantization

```bash
GPTQ_w8a8_Qwen3.ipynb
```

Experiments with:

- GPTQ quantization
- W8A8 optimization
- Qwen3 compression

---

## QLoRA Fine-tuning

```bash
qlora_merged_ipynb.ipynb
```

Contains:

- QLoRA training workflow
- Model merging
- Fine-tuning experiments

---

## Unsloth + QLoRA

```bash
QLoRA+Unsloth_Qwen3-14B.ipynb
```

Experiments using:

- Unsloth optimization
- QLoRA
- Qwen3-14B

---

# ⚙️ Operational Notes

## Stable SSE Streaming

`main.py` uses:

- Thread producer
- Queue bridge
- Async streaming adapter

to avoid token buffering and ensure stable streaming responses.

---

## Session Persistence

Chat sessions are automatically stored in:

```bash
chat_sessions/
```

Each session is saved after stream completion.

---

# 📈 Future Improvements

- [ ] Docker Compose deployment
- [ ] CI/CD pipeline
- [ ] Automatic crawling scheduler
- [ ] Retrieval evaluation metrics
- [ ] Hybrid BM25 + Dense optimization
- [ ] Multi-agent travel planner
- [ ] Image-aware tourism assistant
- [ ] Voice interaction support

---

# 📖 Main Files Reference

| File | Purpose |
|---|---|
| `main.py` | FastAPI backend & SSE streaming |
| `building_retriever.py` | Core RAG pipeline |
| `vector_embeddings.py` | Embedding generation & Qdrant upsert |
| `data_collection_and_chunking.py` | Crawl & chunk pipeline |
| `crawl_v2.py` | Advanced crawler |
| `config.py` | Environment configuration |
| `react_FE/` | Frontend application |

---

# 🤝 Contributing

Contributions, ideas, and improvements are welcome.

Feel free to:
- Open issues
- Submit pull requests
- Suggest new retrieval strategies
- Improve frontend UX/UI

---

# 📜 License

This project is intended for educational and research purposes.

---

# 👨‍💻 Author

Developed as an AI/NLP project focusing on:

- Retrieval-Augmented Generation
- Hybrid Search
- Vietnamese Tourism QA
- LLM Engineering
- Quantization & Fine-tuning Research

---

# ⭐ If you found this project useful

Please consider giving the repository a star ⭐
