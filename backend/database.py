"""
Database models and connection setup for the RAG Travel Chatbot.
Uses PostgreSQL with SQLAlchemy ORM for persistent chat history.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional, List, Generator
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from config import DATABASE_URL

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False,          # Set to True for SQL debugging
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


# ====================== DATABASE MODELS ======================

class ChatSession(Base):
    """
    Represents a chat session with the user.
    Each session maintains a separate conversation context.
    """
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, index=True, nullable=False)  # UUID
    title = Column(String(200), nullable=False, default="New Chat")
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationship to messages
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ChatSession(session_id={self.session_id}, title={self.title})>"


class Message(Base):
    """
    Represents a single message in a chat session.
    Can be either from user or assistant.
    """
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.session_id"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    context = Column(Text, nullable=True)  # RAG context used for this message
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationship to session
    session = relationship("ChatSession", back_populates="messages")

    def __repr__(self):
        preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(role={self.role}, content={preview})>"


# ====================== DATABASE UTILITIES ======================

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized successfully")


def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Used with FastAPI's Depends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ====================== DATABASE OPERATIONS ======================

def create_session_db(db: Session, session_id: str, title: str = "New Chat") -> ChatSession:
    """Create a new chat session"""
    session = ChatSession(session_id=session_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_db(db: Session, session_id: str) -> Optional[ChatSession]:
    """Get a session by ID"""
    return db.query(ChatSession).filter(ChatSession.session_id == session_id).first()


def list_sessions_db(db: Session, limit: int = 50) -> List[ChatSession]:
    """List all sessions, ordered by most recent"""
    return db.query(ChatSession).filter(ChatSession.is_active == True).order_by(ChatSession.updated_at.desc()).limit(limit).all()


def delete_session_db(db: Session, session_id: str) -> bool:
    """Delete a session and all its messages"""
    session = get_session_db(db, session_id)
    if session:
        db.delete(session)
        db.commit()
        return True
    return False


def update_session_title_db(db: Session, session_id: str, title: str) -> Optional[ChatSession]:
    """Update session title"""
    session = get_session_db(db, session_id)
    if session:
        session.title = title
        session.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(session)
        return session
    return None


def add_message_db(db: Session, session_id: str, role: str, content: str, context: Optional[str] = None) -> Message:
    """Add a message to a session"""
    message = Message(
        session_id=session_id,
        role=role,
        content=content,
        context=context
    )
    db.add(message)
    
    # Update session's updated_at timestamp
    session = get_session_db(db, session_id)
    if session:
        session.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    return message


def get_session_messages_db(db: Session, session_id: str, limit: int = 100) -> List[Message]:
    """Get all messages for a session"""
    return db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at.asc()).limit(limit).all()


def get_conversation_history(db: Session, session_id: str, max_messages: int = 10) -> List[dict]:
    """
    Get recent conversation history for context.
    Returns list of dicts with role and content.
    """
    messages = db.query(Message).filter(
        Message.session_id == session_id
    ).order_by(Message.created_at.desc()).limit(max_messages).all()
    
    # Reverse to get chronological order
    messages = list(reversed(messages))
    
    return [{"role": msg.role, "content": msg.content} for msg in messages]


if __name__ == "__main__":
    # Initialize database when run directly
    print("Initializing database...")
    init_db()
