"""
RAG Evaluation Pipeline using Ragas Framework (Reference-Free)
================================================================

This script evaluates the RAG chatbot's quality using local Ollama models
WITHOUT requiring ground truth answers.

Metrics implemented:
- Faithfulness: Checks if answers are grounded in retrieved context (detects hallucinations)
- Answer Relevancy: Checks if answers address the user's query

Usage:
    python evaluate_rag.py
    
    Or programmatically:
    from evaluate_rag import run_eval
    result = run_eval("What is the food in Da Nang?")
"""
from __future__ import annotations
from typing import List, Dict, Any, Tuple
import json
from datetime import datetime

# Ragas imports
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from datasets import Dataset

# LangChain imports for local models
from langchain_community.chat_models import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings

# Import existing RAG components
from building_retriever import (
    rewrite_query_llm,
    route_query_llm,
    retrieve_mmr,
    rerank_bge,
    build_context,
    embeddings as rag_embeddings,
    EMBED_MODEL
)
from config import OLLAMA_BASE_URL, GENERATOR_MODEL


# ====================== ENHANCED RAG PIPELINE ======================

def rag_pipeline_with_sources(query: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Enhanced RAG pipeline that returns both context and source documents.
    Required for Ragas evaluation.
    
    Args:
        query: User's question
        verbose: Print debug information
        
    Returns:
        dict with:
            - context: Combined context string
            - contexts: List of individual document texts (for Ragas)
            - documents: List of Document objects
            - metadata: Pipeline information
    """
    if verbose:
        print(f"📝 User query: {query}")

    # 1. Rewrite
    rewritten = rewrite_query_llm(query)
    if verbose:
        print(f"✍️  Rewritten: {rewritten}")

    # 2. Routing
    route_info = route_query_llm(rewritten)
    if verbose:
        print(f"🧭 Routing: {route_info}")

    # 3. Retrieve (MMR)
    docs = retrieve_mmr(
        query=rewritten,
        k=25,
        fetch_k=50,
        qdrant_filter=route_info["filter"],
    )
    if verbose:
        print(f"📚 Retrieved: {len(docs)} documents")

    # 4. Re-rank (BGE)
    reranked = rerank_bge(rewritten, docs, top_n=8)
    if verbose:
        print(f"⭐ Reranked: {len(reranked)} documents")

    # 5. Build context
    context = build_context(reranked)
    
    # 6. Extract individual context strings (for Ragas)
    contexts = [doc.page_content for doc in reranked]

    return {
        "context": context,
        "contexts": contexts,  # List of strings (required by Ragas)
        "documents": reranked,
        "metadata": {
            "query_original": query,
            "query_rewritten": rewritten,
            "routing": route_info,
            "num_retrieved": len(docs),
            "num_reranked": len(reranked)
        }
    }


# ====================== RAGAS SETUP ======================

def setup_ragas_models():
    """
    Configure Ragas to use local Ollama models instead of OpenAI.
    
    Returns:
        tuple: (critic_llm, embeddings)
    """
    print("⚙️  Setting up Ragas with local models...")
    
    # 1. Setup Critic LLM (for evaluation metrics)
    critic_llm = ChatOllama(
        model=GENERATOR_MODEL,
        base_url=OLLAMA_BASE_URL,
        temperature=0.0,  # Deterministic for evaluation
    )
    print(f"✅ Critic LLM: {GENERATOR_MODEL}")
    
    # 2. Setup Embeddings (same as RAG pipeline)
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )
    print(f"✅ Embeddings: {EMBED_MODEL}")
    
    return critic_llm, embeddings


def create_ragas_metrics(llm, embeddings):
    """
    Create Ragas metrics with custom LLM and embeddings.
    
    Args:
        llm: LangChain LLM for evaluation
        embeddings: LangChain embeddings
        
    Returns:
        list: Ragas metric objects
    """
    # Configure metrics with custom models
    faithfulness_metric = faithfulness
    faithfulness_metric.llm = llm
    
    answer_relevancy_metric = answer_relevancy
    answer_relevancy_metric.llm = llm
    answer_relevancy_metric.embeddings = embeddings
    
    return [faithfulness_metric, answer_relevancy_metric]


# ====================== ANSWER GENERATION ======================

def generate_answer_simple(query: str, context: str) -> str:
    """
    Simple answer generation for evaluation.
    In production, this would use your generator.py
    
    Args:
        query: User's question
        context: Retrieved context
        
    Returns:
        Generated answer string
    """
    from building_retriever import chat_llm
    
    prompt = f"""Bạn là trợ lý du lịch Việt Nam. Trả lời câu hỏi dựa trên thông tin được cung cấp.

THÔNG TIN:
{context}

CÂU HỎI: {query}

HƯỚNG DẪN:
- Chỉ sử dụng thông tin từ phần THÔNG TIN
- Trả lời ngắn gọn, súc tích
- Nếu không có thông tin, nói rõ

TRẢ LỜI:"""

    answer = chat_llm([{"role": "user", "content": prompt}])
    return answer


# ====================== EVALUATION PIPELINE ======================

def evaluate_single_query(
    query: str,
    verbose: bool = True
) -> Dict[str, Any]:
    """
    Evaluate a single query through the RAG pipeline (Reference-Free).
    
    Args:
        query: User's question
        verbose: Print debug information
        
    Returns:
        dict with evaluation results containing:
            - query: Original user query
            - answer: Generated answer
            - contexts: Retrieved context chunks
            - metadata: RAG pipeline metadata
            - scores: Evaluation scores (faithfulness, answer_relevancy)
            - timestamp: Evaluation timestamp
    """
    print("\n" + "="*70)
    print(f"🔍 EVALUATING QUERY: {query}")
    print("="*70 + "\n")
    
    # 1. Run RAG pipeline to get context
    rag_result = rag_pipeline_with_sources(query, verbose=verbose)
    
    # 2. Generate answer
    if verbose:
        print("\n🤖 Generating answer...")
    answer = generate_answer_simple(query, rag_result["context"])
    if verbose:
        print(f"📝 Answer: {answer[:200]}..." if len(answer) > 200 else f"📝 Answer: {answer}")
    
    # 3. Prepare data for Ragas (Reference-Free: only question, answer, contexts)
    eval_data = {
        "question": [query],
        "answer": [answer],
        "contexts": [rag_result["contexts"]],  # List of lists of strings
    }
    
    # 4. Create Dataset
    dataset = Dataset.from_dict(eval_data)
    
    # 5. Setup Ragas
    critic_llm, embeddings = setup_ragas_models()
    metrics = create_ragas_metrics(critic_llm, embeddings)
    
    # 6. Run evaluation
    if verbose:
        print("\n📊 Running Ragas evaluation...")
    
    result = evaluate(
        dataset,
        metrics=metrics,
    )
    
    # 7. Compile results
    evaluation_result = {
        "query": query,
        "answer": answer,
        "contexts": rag_result["contexts"],
        "metadata": rag_result["metadata"],
        "scores": {
            "faithfulness": result["faithfulness"],
            "answer_relevancy": result["answer_relevancy"],
        },
        "timestamp": datetime.utcnow().isoformat()
    }
    
    return evaluation_result


def evaluate_batch(
    queries: List[str],
    save_results: bool = True,
    output_file: str = "evaluation_results.json"
) -> List[Dict[str, Any]]:
    """
    Evaluate multiple queries in batch (Reference-Free).
    
    Args:
        queries: List of query strings (no ground truth needed)
        save_results: Whether to save results to JSON
        output_file: Output file path
        
    Returns:
        List of evaluation results
    """
    results = []
    
    print(f"\n{'='*70}")
    print(f"🚀 BATCH EVALUATION: {len(queries)} queries")
    print(f"{'='*70}\n")
    
    for i, query in enumerate(queries, 1):
        print(f"\n--- Query {i}/{len(queries)} ---")
        print(f"Query: {query}")
        
        result = evaluate_single_query(
            query=query,
            verbose=False  # Less verbose for batch
        )
        
        results.append(result)
        
        # Print summary
        print(f"\n📊 Scores:")
        print(f"   Faithfulness: {result['scores']['faithfulness']:.4f}")
        print(f"   Answer Relevancy: {result['scores']['answer_relevancy']:.4f}")
    
    # Calculate average scores
    avg_faithfulness = sum(r['scores']['faithfulness'] for r in results) / len(results)
    avg_relevancy = sum(r['scores']['answer_relevancy'] for r in results) / len(results)
    
    print(f"\n{'='*70}")
    print("📈 OVERALL RESULTS")
    print(f"{'='*70}")
    print(f"Average Faithfulness: {avg_faithfulness:.4f}")
    print(f"Average Answer Relevancy: {avg_relevancy:.4f}")
    print(f"{'='*70}\n")
    
    # Save results
    if save_results:
        summary = {
            "evaluation_date": datetime.utcnow().isoformat(),
            "num_queries": len(queries),
            "average_scores": {
                "faithfulness": avg_faithfulness,
                "answer_relevancy": avg_relevancy
            },
            "results": results
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Results saved to: {output_file}\n")
    
    return results


# ====================== TEST CASES ======================

# Sample test queries for evaluation (Reference-Free: no ground truth needed)
SAMPLE_TEST_QUERIES = [
    "Món ăn nổi tiếng ở Đà Nẵng là gì?",
    "Địa điểm du lịch ở Hà Nội?",
    "Làm sao để đi từ sân bay Tân Sơn Nhất vào trung tâm TP.HCM?",
    "Mùa nào đẹp nhất để đi Sapa?",
    "Chi phí du lịch Phú Quốc khoảng bao nhiêu?",
]


# ====================== CONVENIENCE FUNCTIONS ======================

def run_eval(query: str, verbose: bool = True) -> Dict[str, Any]:
    """
    Convenience function for quick evaluation of a single query.
    
    Args:
        query: User's question
        verbose: Print detailed information
        
    Returns:
        Evaluation result dictionary
        
    Example:
        >>> result = run_eval("What is the food in Da Nang?")
        >>> print(f"Faithfulness: {result['scores']['faithfulness']}")
    """
    return evaluate_single_query(query, verbose=verbose)


# ====================== MAIN EXECUTION ======================

def main():
    """Main execution function"""
    print("\n" + "="*70)
    print("🎯 RAG EVALUATION PIPELINE - RAGAS FRAMEWORK (REFERENCE-FREE)")
    print("="*70 + "\n")
    
    # Option 1: Single query evaluation (detailed)
    print("📍 MODE: Single Query Evaluation\n")
    
    test_query = "Có những món ăn nào nổi tiếng ở Đà Nẵng?"
    
    result = evaluate_single_query(
        query=test_query,
        verbose=True
    )
    
    # Print detailed results
    print("\n" + "="*70)
    print("📊 EVALUATION RESULTS")
    print("="*70)
    print(f"Query: {result['query']}")
    print(f"\nAnswer: {result['answer']}")
    print(f"\nNumber of Context Chunks: {len(result['contexts'])}")
    print(f"\nScores:")
    print(f"  ✅ Faithfulness: {result['scores']['faithfulness']:.4f}")
    print(f"     (How well the answer is grounded in context - detects hallucinations)")
    print(f"  ✅ Answer Relevancy: {result['scores']['answer_relevancy']:.4f}")
    print(f"     (How well the answer addresses the query)")
    print("="*70 + "\n")
    
    # Option 2: Batch evaluation (uncomment to use)
    # print("\n📍 MODE: Batch Evaluation\n")
    # evaluate_batch(SAMPLE_TEST_QUERIES, save_results=True)


if __name__ == "__main__":
    main()
