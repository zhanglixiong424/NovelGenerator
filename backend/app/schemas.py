from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ─── Auth ───────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class SetupRequest(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    username: str
    is_admin: bool
    created_at: datetime


# ─── AI Provider Config ────────────────────────────────

class AIProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider_type: str = Field(pattern=r"^(kimi|openai|deepseek|custom)$")
    api_key: str = Field(min_length=1)
    base_url: str = Field(min_length=1, max_length=500)
    model_name: str = Field(min_length=1, max_length=100)
    priority: int = Field(default=1, ge=1, le=100)
    is_enabled: bool = True
    max_tokens: int = Field(default=4096, ge=256, le=128000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)


class AIProviderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    provider_type: Optional[str] = Field(default=None, pattern=r"^(kimi|openai|deepseek|custom)$")
    api_key: Optional[str] = Field(default=None, min_length=1)
    base_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    model_name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    priority: Optional[int] = Field(default=None, ge=1, le=100)
    is_enabled: Optional[bool] = None
    max_tokens: Optional[int] = Field(default=None, ge=256, le=128000)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)


class AIProviderResponse(BaseModel):
    id: str
    name: str
    provider_type: str
    api_key_masked: str
    base_url: str
    model_name: str
    priority: int
    is_enabled: bool
    max_tokens: int
    temperature: float
    last_test_status: str
    last_test_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class AIProviderTestResult(BaseModel):
    success: bool
    message: str
    latency_ms: Optional[int] = None


# ─── Project ───────────────────────────────────────────

class ProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    genre: str = Field(min_length=1, max_length=50)
    target_platform: str = Field(default="", max_length=50)
    target_word_count: int = Field(default=100000, ge=1000, le=10000000)


class ProjectUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    genre: Optional[str] = Field(default=None, min_length=1, max_length=50)
    target_platform: Optional[str] = Field(default=None, max_length=50)
    target_word_count: Optional[int] = Field(default=None, ge=1000, le=10000000)
    outline: Optional[str] = None
    world_setting: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    title: str
    genre: str
    target_platform: str
    target_word_count: int
    outline: str
    world_setting: str
    status: str
    chapter_count: int = 0
    created_at: datetime
    updated_at: datetime


# ─── Chapter ───────────────────────────────────────────

class ChapterResponse(BaseModel):
    id: str
    chapter_no: int
    title: str
    outline: str
    content: str
    summary: str
    word_count: int
    compliance_status: str
    consistency_status: str
    status: str
    created_at: datetime
    updated_at: datetime


class ChapterUpdate(BaseModel):
    title: Optional[str] = None
    outline: Optional[str] = None
    content: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None


class ChapterListItem(BaseModel):
    id: str
    chapter_no: int
    title: str
    word_count: int
    status: str
    compliance_status: str
    consistency_status: str


# ─── Knowledge Base ────────────────────────────────────

class KnowledgeEntityResponse(BaseModel):
    id: str
    entity_type: str
    name: str
    data: str  # JSON string
    summary: str
    is_important: bool
    first_appearance: int
    created_at: datetime
    updated_at: datetime


class KnowledgeEntityUpdate(BaseModel):
    name: Optional[str] = None
    data: Optional[str] = None
    summary: Optional[str] = None
    is_important: Optional[bool] = None


class KnowledgeVersionResponse(BaseModel):
    id: str
    version_no: int
    chapter_no: int
    created_at: datetime
    changes: list["KnowledgeChangeResponse"] = []


class KnowledgeChangeResponse(BaseModel):
    id: str
    entity_type: str
    entity_id: str
    field: str
    old_value: str
    new_value: str
    is_auto_extracted: bool
    is_confirmed: bool
    created_at: datetime


class KnowledgeConfirmRequest(BaseModel):
    version_id: str
    confirmed_change_ids: list[str] = []
    confirm_all: bool = False


class WorkflowStateResponse(BaseModel):
    current_state: str
    current_chapter_no: int
    pending_data: str


# ─── Generation ────────────────────────────────────────

class GenerateRequest(BaseModel):
    trust_mode: bool = False


class BatchGenerateRequest(BaseModel):
    start_chapter: int = 0
    trust_mode: bool = False


class OutlineConfirmRequest(BaseModel):
    outline: Optional[str] = None  # Modified outline, or None to accept as-is


class ExportResponse(BaseModel):
    filename: str
    content: str
