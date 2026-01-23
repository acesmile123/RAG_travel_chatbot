"""
FastAPI main application for the RAG Travel Chatbot.
Provides RESTful API endpoints for chat, session management, and history.
"""
from __future__ import annotations
from typing import Optional, List
from datetime import datetime
import uuid
import asyncio

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

# Import local modules
from database import (
    get_db, init_db,
    create_session_db, get_session_db, list_sessions_db,
    delete_session_db, update_session_title_db,
    add_message_db, get_session_messages_db, get_conversation_history
)
from generator import generate_response, generate_session_title
from building_retriever import rag_pipeline


# ====================== FASTAPI APP SETUP ======================

app = FastAPI(
    title="RAG Travel Chatbot API",
    description="API for Vietnam Travel Chatbot with RAG and conversational memory",
    version="1.0.0"
)

# CORS Configuration - Allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite default dev server
        "http://localhost:3000",  # Alternative React port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ====================== PYDANTIC MODELS ======================

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., min_length=1, max_length=2000, description="User's message")
    session_id: Optional[str] = Field(None, description="Chat session ID (creates new if not provided)")
    stream: bool = Field(False, description="Whether to stream the response")


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    session_id: str
    message: str
    context: Optional[str] = None
    created_at: datetime


class SessionCreate(BaseModel):
    """Request model for creating a session"""
    title: Optional[str] = Field("New Chat", max_length=200)


class SessionResponse(BaseModel):
    """Response model for session information"""
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class MessageResponse(BaseModel):
    """Response model for message information"""
    id: int
    role: str
    content: str
    created_at: datetime


class SessionDetailResponse(BaseModel):
    """Response model for session with messages"""
    session_id: str
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse]


# ====================== STARTUP/SHUTDOWN EVENTS ======================

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    init_db()
    print("✅ FastAPI server started")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("👋 FastAPI server shutting down")


# ====================== API ENDPOINTS ======================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "online",
        "message": "RAG Travel Chatbot API",
        "version": "1.0.0"
    }


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Main chat endpoint.
    Processes user message through RAG pipeline and generates response.
    Supports both streaming and non-streaming responses.
    """
    try:
        # 1. Get or create session
        session_id = request.session_id
        if not session_id:
            session_id = str(uuid.uuid4())
            create_session_db(db, session_id, title="New Chat")
        else:
            # Verify session exists
            session = get_session_db(db, session_id)
            if not session:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Session {session_id} not found"
                )
        
        # 2. Save user message
        add_message_db(db, session_id, "user", request.message)
        
        # 3. Get RAG context
        print(f"[RAG] Processing query: {request.message}")
        rag_context = rag_pipeline(request.message)
        print(f"[RAG] Retrieved context length: {len(rag_context)}")
        
        # 4. Get conversation history for context
        conversation_history = get_conversation_history(db, session_id, max_messages=6)
        
        # 5. Generate response
        if request.stream:
            # Streaming response
            async def generate_stream():
                full_response = ""
                async for chunk in await generate_response(
                    request.message,
                    rag_context,
                    conversation_history,
                    stream=True
                ):
                    full_response += chunk
                    yield chunk
                
                # Save complete response after streaming
                add_message_db(db, session_id, "assistant", full_response, rag_context)
                
                # Update session title if this is the first message
                messages = get_session_messages_db(db, session_id)
                if len(messages) == 2:  # First user message + first assistant response
                    title = await generate_session_title(request.message)
                    update_session_title_db(db, session_id, title)
            
            return StreamingResponse(
                generate_stream(),
                media_type="text/plain"
            )
        else:
            # Non-streaming response
            response_text = await generate_response(
                request.message,
                rag_context,
                conversation_history,
                stream=False
            )
            
            # Save assistant response
            add_message_db(db, session_id, "assistant", response_text, rag_context)
            
            # Update session title if this is the first message
            messages = get_session_messages_db(db, session_id)
            if len(messages) == 2:  # First user message + first assistant response
                title = await generate_session_title(request.message)
                update_session_title_db(db, session_id, title)
            
            return ChatResponse(
                session_id=session_id,
                message=response_text,
                context=rag_context,
                created_at=datetime.utcnow()
            )
    
    except Exception as e:
        print(f"[ERROR] Chat endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing chat: {str(e)}"
        )


@app.post("/api/v1/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    request: SessionCreate,
    db: Session = Depends(get_db)
):
    """Create a new chat session"""
    try:
        session_id = str(uuid.uuid4())
        session = create_session_db(db, session_id, request.title)
        
        return SessionResponse(
            session_id=session.session_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=0
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating session: {str(e)}"
        )


@app.get("/api/v1/sessions", response_model=List[SessionResponse])
async def list_sessions(
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """List all chat sessions"""
    try:
        sessions = list_sessions_db(db, limit)
        
        return [
            SessionResponse(
                session_id=s.session_id,
                title=s.title,
                created_at=s.created_at,
                updated_at=s.updated_at,
                message_count=len(s.messages)
            )
            for s in sessions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing sessions: {str(e)}"
        )


@app.get("/api/v1/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Get a specific session with all its messages"""
    try:
        session = get_session_db(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        messages = get_session_messages_db(db, session_id)
        
        return SessionDetailResponse(
            session_id=session.session_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            messages=[
                MessageResponse(
                    id=m.id,
                    role=m.role,
                    content=m.content,
                    created_at=m.created_at
                )
                for m in messages
            ]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting session: {str(e)}"
        )


@app.delete("/api/v1/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """Delete a chat session and all its messages"""
    try:
        success = delete_session_db(db, session_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting session: {str(e)}"
        )


@app.patch("/api/v1/sessions/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: str,
    title: str,
    db: Session = Depends(get_db)
):
    """Update session title"""
    try:
        session = update_session_title_db(db, session_id, title)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session {session_id} not found"
            )
        
        return SessionResponse(
            session_id=session.session_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(session.messages)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating session: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    # Run with: python main.py
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
