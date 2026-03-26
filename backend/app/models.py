import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import relationship

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ─── User ───────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    projects = relationship("NovelProject", back_populates="user", cascade="all, delete-orphan")
    ai_configs = relationship("AIProviderConfig", back_populates="user", cascade="all, delete-orphan")


# ─── Novel Project ──────────────────────────────────────

class NovelProject(Base):
    __tablename__ = "novel_projects"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    genre = Column(String(50), nullable=False)
    target_platform = Column(String(50), default="")
    target_word_count = Column(Integer, default=100000)
    outline = Column(Text, default="")
    world_setting = Column(Text, default="")
    status = Column(String(30), default="idle")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="projects")
    chapters = relationship("Chapter", back_populates="project", cascade="all, delete-orphan",
                            order_by="Chapter.chapter_no")
    knowledge_entities = relationship("KnowledgeEntity", back_populates="project", cascade="all, delete-orphan")
    knowledge_versions = relationship("KnowledgeVersion", back_populates="project", cascade="all, delete-orphan")
    workflow_state = relationship("WorkflowStateRecord", back_populates="project", uselist=False,
                                  cascade="all, delete-orphan")
    timeline_events = relationship("TimelineEvent", back_populates="project", cascade="all, delete-orphan")


# ─── Chapter ────────────────────────────────────────────

class Chapter(Base):
    __tablename__ = "chapters"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("novel_projects.id"), nullable=False, index=True)
    chapter_no = Column(Integer, nullable=False)
    title = Column(String(200), default="")
    outline = Column(Text, default="")
    content = Column(Text, default="")
    summary = Column(Text, default="")
    word_count = Column(Integer, default=0)
    compliance_status = Column(String(20), default="unchecked")
    consistency_status = Column(String(20), default="unchecked")
    status = Column(String(20), default="draft")
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    project = relationship("NovelProject", back_populates="chapters")
    generation_logs = relationship("GenerationLog", back_populates="chapter", cascade="all, delete-orphan")


# ─── AI Provider Config ────────────────────────────────

class AIProviderConfig(Base):
    __tablename__ = "ai_provider_configs"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    provider_type = Column(String(30), nullable=False)  # kimi / openai / deepseek / custom
    api_key_encrypted = Column(Text, nullable=False)
    base_url = Column(String(500), nullable=False)
    model_name = Column(String(100), nullable=False)
    priority = Column(Integer, default=1)
    is_enabled = Column(Boolean, default=True)
    max_tokens = Column(Integer, default=4096)
    temperature = Column(Float, default=0.7)
    last_test_status = Column(String(20), default="untested")
    last_test_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="ai_configs")


# ─── Knowledge Base ─────────────────────────────────────

class KnowledgeEntity(Base):
    __tablename__ = "knowledge_entities"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("novel_projects.id"), nullable=False, index=True)
    entity_type = Column(String(30), nullable=False, index=True)  # character/item/skill/faction/location
    name = Column(String(200), nullable=False)
    data = Column(Text, default="{}")  # JSON
    summary = Column(Text, default="")
    is_important = Column(Boolean, default=False)
    first_appearance = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    project = relationship("NovelProject", back_populates="knowledge_entities")


class KnowledgeVersion(Base):
    __tablename__ = "knowledge_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("novel_projects.id"), nullable=False, index=True)
    version_no = Column(Integer, nullable=False)
    chapter_no = Column(Integer, default=0)
    created_at = Column(DateTime, default=utcnow)

    project = relationship("NovelProject", back_populates="knowledge_versions")
    changes = relationship("KnowledgeChange", back_populates="version", cascade="all, delete-orphan")


class KnowledgeChange(Base):
    __tablename__ = "knowledge_changes"

    id = Column(String, primary_key=True, default=generate_uuid)
    version_id = Column(String, ForeignKey("knowledge_versions.id"), nullable=False, index=True)
    entity_type = Column(String(30), nullable=False)
    entity_id = Column(String, nullable=False)
    field = Column(String(100), nullable=False)
    old_value = Column(Text, default="")  # JSON
    new_value = Column(Text, default="")  # JSON
    is_auto_extracted = Column(Boolean, default=True)
    is_confirmed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=utcnow)

    version = relationship("KnowledgeVersion", back_populates="changes")


# ─── Workflow State ─────────────────────────────────────

class WorkflowStateRecord(Base):
    __tablename__ = "workflow_states"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("novel_projects.id"), nullable=False, unique=True)
    current_state = Column(String(30), default="idle")
    current_chapter_no = Column(Integer, default=0)
    pending_data = Column(Text, default="{}")  # JSON
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    project = relationship("NovelProject", back_populates="workflow_state")


# ─── Generation Log ────────────────────────────────────

class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id = Column(String, primary_key=True, default=generate_uuid)
    chapter_id = Column(String, ForeignKey("chapters.id"), nullable=False, index=True)
    provider_id = Column(String, nullable=False)
    model_name = Column(String(100), default="")
    prompt_summary = Column(Text, default="")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)
    status = Column(String(20), default="success")
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=utcnow)

    chapter = relationship("Chapter", back_populates="generation_logs")


# ─── Timeline Event ────────────────────────────────────

class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("novel_projects.id"), nullable=False, index=True)
    chapter_no = Column(Integer, default=0)
    event_type = Column(String(30), nullable=False)
    description = Column(Text, default="")
    related_entities = Column(Text, default="[]")  # JSON array
    created_at = Column(DateTime, default=utcnow)

    project = relationship("NovelProject", back_populates="timeline_events")
