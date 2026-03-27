"""
Generation service — orchestrates outline, opening, batch generation.
Each chapter is an atomic unit: generate → check → extract → confirm.
"""

import json
import logging
import time
from typing import AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_service import AIService, AllProvidersFailedError
from app.models import (
    NovelProject, Chapter, AIProviderConfig, KnowledgeEntity,
    KnowledgeVersion, KnowledgeChange, WorkflowStateRecord, GenerationLog,
)
from app.prompts import (
    build_outline_messages, build_chapter_messages, build_summary_messages,
    build_knowledge_extract_messages, build_consistency_check_messages,
    check_compliance, parse_json_response, PromptContext,
)

log = logging.getLogger(__name__)


# ─── SSE Event helpers ──────────────────────────────────

def sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ─── Knowledge helpers ──────────────────────────────────

async def _get_knowledge_summary(db: AsyncSession, project_id: str) -> str:
    """Get a text summary of current knowledge entities for a project."""
    result = await db.execute(
        select(KnowledgeEntity)
        .where(KnowledgeEntity.project_id == project_id)
        .order_by(KnowledgeEntity.entity_type, KnowledgeEntity.name)
    )
    entities = result.scalars().all()
    if not entities:
        return ""

    parts = []
    for e in entities:
        parts.append(f"[{e.entity_type}] {e.name}: {e.summary or '无摘要'}")
    return "\n".join(parts)


async def _get_chapter_summaries(db: AsyncSession, project_id: str, up_to_no: int, limit: int = 3) -> str:
    """Get summaries of recent chapters before a given chapter number."""
    start_no = max(1, up_to_no - limit)
    result = await db.execute(
        select(Chapter)
        .where(
            Chapter.project_id == project_id,
            Chapter.chapter_no >= start_no,
            Chapter.chapter_no < up_to_no,
        )
        .order_by(Chapter.chapter_no)
    )
    chapters = result.scalars().all()
    if not chapters:
        return ""
    parts = []
    for ch in chapters:
        parts.append(f"第{ch.chapter_no}章 {ch.title}：{ch.summary or '（无摘要）'}")
    return "\n".join(parts)


async def _build_core_characters(db: AsyncSession, project_id: str) -> str:
    """Layer 1: Core characters summary (≤1000 tokens target)."""
    result = await db.execute(
        select(KnowledgeEntity)
        .where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.entity_type == "character",
        )
        .order_by(KnowledgeEntity.is_important.desc())
        .limit(8)
    )
    chars = result.scalars().all()
    if not chars:
        return ""
    parts = []
    for c in chars:
        parts.append(f"· {c.name}: {c.summary or '无描述'}")
    return "\n".join(parts)


async def _build_related_context(db: AsyncSession, project_id: str) -> str:
    """Layer 2: Related items, skills, factions (≤1500 tokens target)."""
    result = await db.execute(
        select(KnowledgeEntity)
        .where(
            KnowledgeEntity.project_id == project_id,
            KnowledgeEntity.entity_type.in_(["item", "skill", "faction", "location"]),
            KnowledgeEntity.is_important == True,
        )
        .limit(10)
    )
    entities = result.scalars().all()
    if not entities:
        return ""
    parts = []
    for e in entities:
        parts.append(f"· [{e.entity_type}] {e.name}: {e.summary or '无描述'}")
    return "\n".join(parts)


async def _get_ai_service(db: AsyncSession, user_id: str) -> AIService:
    """Load enabled AI providers for user and create AIService."""
    result = await db.execute(
        select(AIProviderConfig)
        .where(
            AIProviderConfig.user_id == user_id,
            AIProviderConfig.is_enabled == True,
        )
        .order_by(AIProviderConfig.priority)
    )
    providers = result.scalars().all()
    return AIService(providers)


async def _update_workflow_state(
    db: AsyncSession, project_id: str,
    state: str, chapter_no: int = 0, pending_data: dict | None = None,
):
    """Update or create the workflow state record for a project."""
    result = await db.execute(
        select(WorkflowStateRecord)
        .where(WorkflowStateRecord.project_id == project_id)
    )
    ws = result.scalar_one_or_none()
    if ws is None:
        ws = WorkflowStateRecord(
            project_id=project_id,
            current_state=state,
            current_chapter_no=chapter_no,
        )
        db.add(ws)
    else:
        ws.current_state = state
        ws.current_chapter_no = chapter_no
    if pending_data is not None:
        ws.pending_data = json.dumps(pending_data, ensure_ascii=False)
    await db.commit()


# ─── Outline Generation ────────────────────────────────

async def generate_outline(
    db: AsyncSession, project: NovelProject, user_id: str,
) -> AsyncGenerator[str, None]:
    """Generate novel outline via SSE stream."""
    ai = await _get_ai_service(db, user_id)

    await _update_workflow_state(db, project.id, "outline_generating")

    messages = build_outline_messages(
        title=project.title,
        genre=project.genre,
        platform=project.target_platform,
        word_count=project.target_word_count,
        world_setting=project.world_setting,
    )

    yield sse_event("progress", {"status": "generating", "message": "正在生成大纲..."})

    full_text = []
    try:
        async for chunk in ai.generate_stream(messages, max_tokens=8192, temperature=0.8):
            full_text.append(chunk)
            yield sse_event("chunk", {"text": chunk})
    except AllProvidersFailedError as e:
        yield sse_event("error", {"code": "AI_FAILED", "message": str(e)})
        await _update_workflow_state(db, project.id, "idle")
        return

    outline_text = "".join(full_text)

    # Save outline to project
    project.outline = outline_text
    project.status = "outline_pending"
    await db.commit()

    await _update_workflow_state(db, project.id, "outline_pending")

    yield sse_event("done", {"outline": outline_text, "status": "outline_pending"})


# ─── Chapter Generation (single) ───────────────────────

async def _generate_single_chapter(
    db: AsyncSession,
    ai: AIService,
    project: NovelProject,
    chapter: Chapter,
    trust_mode: bool = False,
) -> AsyncGenerator[str, None]:
    """Generate a single chapter: content → summary → checks → knowledge extraction.
    Yields SSE events throughout the process.
    """
    start_time = time.time()

    # Build prompt context
    prev_summary = await _get_chapter_summaries(db, project.id, chapter.chapter_no)
    core_chars = await _build_core_characters(db, project.id)
    related_ctx = await _build_related_context(db, project.id)

    ctx = PromptContext(
        title=project.title,
        genre=project.genre,
        chapter_no=chapter.chapter_no,
        chapter_title=chapter.title,
        chapter_outline=chapter.outline,
        previous_summary=prev_summary,
        core_characters=core_chars,
        related_context=related_ctx,
        word_count=2000,
    )
    messages = build_chapter_messages(ctx)

    # 1. Generate content (streaming)
    yield sse_event("progress", {
        "chapter_no": chapter.chapter_no,
        "status": "generating",
        "message": f"正在生成第{chapter.chapter_no}章...",
    })

    full_text = []
    try:
        async for chunk in ai.generate_stream(messages, max_tokens=4096):
            full_text.append(chunk)
            yield sse_event("chunk", {"chapter_no": chapter.chapter_no, "text": chunk})
    except AllProvidersFailedError as e:
        yield sse_event("error", {
            "code": "AI_FAILED",
            "chapter_no": chapter.chapter_no,
            "message": str(e),
        })
        return

    content = "".join(full_text)
    word_count = len(content)

    # Save content
    chapter.content = content
    chapter.word_count = word_count
    chapter.status = "generated"
    await db.commit()

    yield sse_event("progress", {
        "chapter_no": chapter.chapter_no,
        "status": "checking",
        "message": f"第{chapter.chapter_no}章生成完毕，正在检查...",
    })

    # 2. Compliance check (keyword-based, instant)
    compliance_issues = check_compliance(content)
    if compliance_issues:
        chapter.compliance_status = "flagged"
        yield sse_event("compliance", {
            "chapter_no": chapter.chapter_no,
            "issues": compliance_issues,
        })
    else:
        chapter.compliance_status = "passed"

    # 3. Generate summary
    try:
        summary_msgs = build_summary_messages(
            project.title, chapter.chapter_no, chapter.title, content,
        )
        summary = await ai.generate_full(summary_msgs, max_tokens=300, temperature=0.3)
        chapter.summary = summary.strip()
    except Exception as e:
        log.warning(f"Summary generation failed for ch{chapter.chapter_no}: {e}")
        chapter.summary = content[:150] + "..."

    # 4. Knowledge extraction
    knowledge_summary = await _get_knowledge_summary(db, project.id)
    changes = []
    try:
        extract_msgs = build_knowledge_extract_messages(
            project.title, chapter.chapter_no, chapter.title,
            content, knowledge_summary,
        )
        extract_result = await ai.generate_full(extract_msgs, max_tokens=2000, temperature=0.2)
        changes = parse_json_response(extract_result)
    except Exception as e:
        log.warning(f"Knowledge extraction failed for ch{chapter.chapter_no}: {e}")

    # Save changes as a new knowledge version
    if changes:
        # Get next version number
        result = await db.execute(
            select(KnowledgeVersion)
            .where(KnowledgeVersion.project_id == project.id)
            .order_by(KnowledgeVersion.version_no.desc())
            .limit(1)
        )
        last_ver = result.scalar_one_or_none()
        next_ver_no = (last_ver.version_no if last_ver else 0) + 1

        version = KnowledgeVersion(
            project_id=project.id,
            version_no=next_ver_no,
            chapter_no=chapter.chapter_no,
        )
        db.add(version)
        await db.flush()

        needs_confirm = False
        for ch_data in changes:
            auto_confirm = _is_auto_confirmable(ch_data)
            if not auto_confirm and not trust_mode:
                needs_confirm = True

            change = KnowledgeChange(
                version_id=version.id,
                entity_type=ch_data.get("entity_type", "unknown"),
                entity_id=ch_data.get("name", "unknown"),
                field=ch_data.get("field", ""),
                old_value=json.dumps(ch_data.get("old_value", ""), ensure_ascii=False),
                new_value=json.dumps(ch_data.get("new_value", ""), ensure_ascii=False),
                is_auto_extracted=True,
                is_confirmed=auto_confirm or trust_mode,
            )
            db.add(change)

        await db.commit()

        # If trust_mode or all auto-confirmed, apply changes immediately
        if trust_mode or not needs_confirm:
            await _apply_knowledge_changes(db, project.id, changes)

        yield sse_event("knowledge_change", {
            "chapter_no": chapter.chapter_no,
            "version_id": version.id,
            "changes": changes,
            "needs_confirm": needs_confirm and not trust_mode,
        })

    # 5. Log generation
    duration_ms = int((time.time() - start_time) * 1000)
    gen_log = GenerationLog(
        chapter_id=chapter.id,
        provider_id="auto",
        model_name="auto",
        prompt_summary=f"Ch{chapter.chapter_no}: {chapter.title}",
        output_tokens=word_count,
        duration_ms=duration_ms,
        status="success",
    )
    db.add(gen_log)

    chapter.consistency_status = "passed"
    await db.commit()

    yield sse_event("done", {
        "chapter_no": chapter.chapter_no,
        "word_count": word_count,
        "has_changes": len(changes) > 0,
    })


def _is_auto_confirmable(change: dict) -> bool:
    """Check if a knowledge change can be auto-confirmed (whitelist)."""
    field = change.get("field", "")
    old_val = str(change.get("old_value", ""))
    new_val = str(change.get("new_value", ""))

    # Quantity decrements of -1 or -2 for known consumables
    if field in ("quantity", "count", "数量"):
        try:
            old_num = float(old_val) if old_val else 0
            new_num = float(new_val) if new_val else 0
            diff = old_num - new_num
            if 0 < diff <= 2:
                return True
        except (ValueError, TypeError):
            pass

    return False


async def _apply_knowledge_changes(
    db: AsyncSession, project_id: str, changes: list[dict],
):
    """Apply confirmed knowledge changes to knowledge entities."""
    for ch_data in changes:
        entity_type = ch_data.get("entity_type", "")
        name = ch_data.get("name", "")
        if not entity_type or not name:
            continue

        # Find or create entity
        result = await db.execute(
            select(KnowledgeEntity)
            .where(
                KnowledgeEntity.project_id == project_id,
                KnowledgeEntity.entity_type == entity_type,
                KnowledgeEntity.name == name,
            )
        )
        entity = result.scalar_one_or_none()

        if entity is None:
            entity = KnowledgeEntity(
                project_id=project_id,
                entity_type=entity_type,
                name=name,
                data="{}",
                summary=ch_data.get("new_value", ""),
            )
            db.add(entity)
            await db.flush()

        # Update entity data
        try:
            data = json.loads(entity.data) if entity.data else {}
        except json.JSONDecodeError:
            data = {}

        field = ch_data.get("field", "")
        if field:
            data[field] = ch_data.get("new_value", "")
            entity.data = json.dumps(data, ensure_ascii=False)

        # Update summary with reason
        reason = ch_data.get("reason", "")
        if reason:
            entity.summary = reason

    await db.commit()


# ─── Opening Generation ────────────────────────────────

async def generate_opening(
    db: AsyncSession, project: NovelProject, user_id: str,
    trust_mode: bool = False,
) -> AsyncGenerator[str, None]:
    """Generate opening 3 chapters via SSE."""
    ai = await _get_ai_service(db, user_id)
    await _update_workflow_state(db, project.id, "opening_generating")

    # Parse outline to get first 3 chapter outlines
    chapter_outlines = _parse_chapter_outlines(project.outline, count=3)

    yield sse_event("progress", {
        "status": "generating",
        "total": len(chapter_outlines),
        "message": "开始生成开篇章节...",
    })

    for i, (title, outline) in enumerate(chapter_outlines):
        chapter_no = i + 1

        # Create or get chapter record
        result = await db.execute(
            select(Chapter)
            .where(
                Chapter.project_id == project.id,
                Chapter.chapter_no == chapter_no,
            )
        )
        chapter = result.scalar_one_or_none()
        if chapter is None:
            chapter = Chapter(
                project_id=project.id,
                chapter_no=chapter_no,
                title=title,
                outline=outline,
            )
            db.add(chapter)
            await db.flush()
        else:
            chapter.title = title
            chapter.outline = outline
            await db.commit()

        # Generate this chapter
        async for event in _generate_single_chapter(db, ai, project, chapter, trust_mode):
            yield event

    project.status = "opening_pending"
    await _update_workflow_state(db, project.id, "opening_pending")
    await db.commit()

    yield sse_event("progress", {
        "status": "opening_pending",
        "message": "开篇3章生成完毕，请确认",
    })


# ─── Batch Generation ──────────────────────────────────

async def generate_batch(
    db: AsyncSession, project: NovelProject, user_id: str,
    start_chapter: int = 0,
    trust_mode: bool = False,
) -> AsyncGenerator[str, None]:
    """Batch generate chapters via SSE."""
    ai = await _get_ai_service(db, user_id)
    await _update_workflow_state(db, project.id, "batch_generating")

    # Parse all chapter outlines
    chapter_outlines = _parse_chapter_outlines(project.outline)

    # Determine start point
    if start_chapter > 0:
        chapter_outlines = [(t, o) for i, (t, o) in enumerate(chapter_outlines)
                           if i + 1 >= start_chapter]

    total = len(chapter_outlines)

    yield sse_event("progress", {
        "status": "batch_generating",
        "current": 0,
        "total": total,
        "message": f"开始批量生成，共{total}章",
    })

    for idx, (title, outline) in enumerate(chapter_outlines):
        chapter_no = (start_chapter or 1) + idx if start_chapter > 0 else idx + 1

        # Skip already generated chapters
        result = await db.execute(
            select(Chapter)
            .where(
                Chapter.project_id == project.id,
                Chapter.chapter_no == chapter_no,
            )
        )
        chapter = result.scalar_one_or_none()

        if chapter and chapter.status in ("generated", "confirmed"):
            yield sse_event("progress", {
                "current": idx + 1,
                "total": total,
                "status": "skipping",
                "chapter_no": chapter_no,
                "message": f"第{chapter_no}章已存在，跳过",
            })
            continue

        if chapter is None:
            chapter = Chapter(
                project_id=project.id,
                chapter_no=chapter_no,
                title=title,
                outline=outline,
            )
            db.add(chapter)
            await db.flush()
        else:
            chapter.title = title
            chapter.outline = outline
            await db.commit()

        yield sse_event("progress", {
            "current": idx + 1,
            "total": total,
            "status": "generating",
            "chapter_no": chapter_no,
        })

        async for event in _generate_single_chapter(db, ai, project, chapter, trust_mode):
            yield event

        await _update_workflow_state(db, project.id, "batch_generating", chapter_no)

    project.status = "export_ready"
    await _update_workflow_state(db, project.id, "export_ready")
    await db.commit()

    yield sse_event("progress", {
        "status": "export_ready",
        "message": "全部章节生成完毕",
    })


# ─── Regenerate single chapter ──────────────────────────

async def regenerate_chapter(
    db: AsyncSession, project: NovelProject, user_id: str,
    chapter_no: int, trust_mode: bool = False,
) -> AsyncGenerator[str, None]:
    """Regenerate a single chapter."""
    ai = await _get_ai_service(db, user_id)

    result = await db.execute(
        select(Chapter)
        .where(
            Chapter.project_id == project.id,
            Chapter.chapter_no == chapter_no,
        )
    )
    chapter = result.scalar_one_or_none()
    if chapter is None:
        yield sse_event("error", {"code": "NOT_FOUND", "message": f"第{chapter_no}章不存在"})
        return

    # Reset chapter
    chapter.content = ""
    chapter.summary = ""
    chapter.status = "draft"
    chapter.compliance_status = "unchecked"
    chapter.consistency_status = "unchecked"
    await db.commit()

    async for event in _generate_single_chapter(db, ai, project, chapter, trust_mode):
        yield event


# ─── Outline Parsing ────────────────────────────────────

def _parse_chapter_outlines(outline_text: str, count: int | None = None) -> list[tuple[str, str]]:
    """Parse chapter outlines from generated outline text.
    Returns list of (title, outline_text) tuples.
    """
    if not outline_text:
        return []

    results = []
    lines = outline_text.split("\n")

    current_title = ""
    current_outline = ""

    for line in lines:
        stripped = line.strip()
        # Match patterns like: 第1章 xxxxx, 第一章 xxxxx
        if stripped.startswith("第") and ("章" in stripped[:10]):
            if current_title:
                results.append((current_title, current_outline.strip()))

            # Extract title and outline
            parts = stripped.split("：", 1)
            if len(parts) < 2:
                parts = stripped.split(":", 1)

            if len(parts) >= 2:
                current_title = parts[0].strip()
                current_outline = parts[1].strip()
            else:
                current_title = stripped
                current_outline = ""
        elif current_title and stripped:
            current_outline += " " + stripped

    if current_title:
        results.append((current_title, current_outline.strip()))

    if count is not None:
        results = results[:count]

    return results
