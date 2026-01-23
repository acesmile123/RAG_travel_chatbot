"""
Response generation module for the RAG Travel Chatbot.
Uses Ollama's GENERATOR_MODEL to create natural, conversational responses.
Incorporates RAG context and conversation history for coherent answers.
"""
from __future__ import annotations
from typing import List, Dict, Optional, AsyncGenerator
import httpx
import json
from config import OLLAMA_BASE_URL, GENERATOR_MODEL, OLLAMA_TIMEOUT


async def generate_response(
    query: str,
    rag_context: str,
    conversation_history: List[Dict[str, str]],
    stream: bool = False
) -> str | AsyncGenerator[str, None]:
    """
    Generate a response using the fine-tuned model.
    
    Args:
        query: User's current question
        rag_context: Retrieved context from RAG pipeline
        conversation_history: Recent conversation messages
        stream: Whether to stream the response
        
    Returns:
        Complete response string or async generator for streaming
    """
    
    # Build the system prompt
    system_prompt = """Bạn là trợ lý du lịch thông minh chuyên về Việt Nam, được huấn luyện để cung cấp thông tin chính xác và thân thiện.

NHIỆM VỤ:
- Trả lời câu hỏi dựa trên CONTEXT được cung cấp
- Sử dụng giọng văn gần gũi, tự nhiên như người bản địa
- Nếu CONTEXT không đủ thông tin, hãy thừa nhận và đưa ra gợi ý chung
- KHÔNG bịa đặt thông tin không có trong CONTEXT
- Trả lời bằng Tiếng Việt

FORMAT:
- Câu trả lời rõ ràng, có cấu trúc
- Sử dụng danh sách hoặc đánh số khi cần
- Thêm emoji để thân thiện hơn (tùy chọn)
"""

    # Build the user message with context
    user_message = f"""CONTEXT:
{rag_context}

---

LỊCH SỬ HỘI THOẠI GẦN ĐÂY:
{_format_conversation_history(conversation_history)}

---

CÂU HỎI HIỆN TẠI:
{query}

---

Dựa trên CONTEXT và LỊCH SỬ trên, hãy trả lời câu hỏi của tôi một cách tự nhiên và hữu ích nhất."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    
    if stream:
        return _stream_response(messages)
    else:
        return await _generate_complete_response(messages)


def _format_conversation_history(history: List[Dict[str, str]]) -> str:
    """Format conversation history for context"""
    if not history:
        return "(Chưa có lịch sử hội thoại)"
    
    formatted = []
    for msg in history:
        role_label = "Người dùng" if msg["role"] == "user" else "Trợ lý"
        formatted.append(f"{role_label}: {msg['content']}")
    
    return "\n".join(formatted)


async def _generate_complete_response(messages: List[Dict[str, str]]) -> str:
    """Generate complete response without streaming"""
    try:
        payload = {
            "model": GENERATOR_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.7,  # Slightly creative for natural responses
                "top_p": 0.9,
                "top_k": 40,
            }
        }
        
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(
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


async def _stream_response(messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
    """Stream response token by token"""
    try:
        payload = {
            "model": GENERATOR_MODEL,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 40,
            }
        }
        
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                content = data["message"]["content"]
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
                            
    except httpx.TimeoutException:
        yield "\n\n[Lỗi: Timeout khi kết nối với Ollama]"
    except httpx.RequestError as e:
        yield f"\n\n[Lỗi: Không thể kết nối tới Ollama - {e}]"
    except Exception as e:
        yield f"\n\n[Lỗi: {str(e)}]"


async def generate_session_title(first_message: str) -> str:
    """
    Generate a short, descriptive title for a chat session based on the first message.
    
    Args:
        first_message: The first user message in the session
        
    Returns:
        A short title (max 50 characters)
    """
    try:
        prompt = f"""Tạo tiêu đề ngắn gọn (tối đa 50 ký tự) cho cuộc hội thoại dựa trên câu hỏi sau:

"{first_message}"

Chỉ trả về tiêu đề, không giải thích."""

        messages = [
            {"role": "user", "content": prompt}
        ]
        
        payload = {
            "model": GENERATOR_MODEL,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Lower temperature for consistent titles
            }
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/chat",
                json=payload
            )
            response.raise_for_status()
            result = response.json()
            title = result["message"]["content"].strip()
            
            # Clean up and limit length
            title = title.replace('"', '').replace("'", "")
            if len(title) > 50:
                title = title[:47] + "..."
                
            return title
            
    except Exception as e:
        print(f"Error generating title: {e}")
        # Fallback to simple truncation
        if len(first_message) > 50:
            return first_message[:47] + "..."
        return first_message


if __name__ == "__main__":
    # Test the generator
    import asyncio
    
    async def test():
        query = "Có những món ăn nào nổi tiếng ở Đà Nẵng?"
        context = "[CHUNK 1]\nMì Quảng là món ăn đặc sản của Đà Nẵng..."
        history = [
            {"role": "user", "content": "Tôi muốn đi du lịch Đà Nẵng"},
            {"role": "assistant", "content": "Đà Nẵng là thành phố đáng sống..."}
        ]
        
        response = await generate_response(query, context, history, stream=False)
        print(response)
    
    asyncio.run(test())
