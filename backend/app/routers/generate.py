"""SSE generation endpoints + workflow state + outline confirm + export."""

import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User, NovelProject, Chapter, WorkflowStateRecord
from app.schemas import (
    GenerateRequest, BatchGenerateRequest, OutlineConfirmRequest,
    WorkflowStateResponse, ExportResponse,
)
from app.generation import (
    generate_outline, generate_opening, generate_batch, regenerate_chapter,
)

router = APIRouter(prefix="/api/projects/{project_id}/generate", tags=["generation"])


async def _get_project(project_id: str, user: User, db: AsyncSession) -> NovelProject:
    result = await db.execute(
        select(NovelProject).where(
            NovelProject.id == project_id,
            NovelProject.user_id == user.id,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


# ─── SSE Endpoints ──────────────────────────────────────

@router.post("/outline")
async def start_outline_generation(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project(project_id, user, db)

    async def stream():
        async for event in generate_outline(db, project, user.id):
            yield event

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/opening")
async def start_opening_generation(
    project_id: str,
    req: GenerateRequest = GenerateRequest(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project(project_id, user, db)

    async def stream():
        async for event in generate_opening(db, project, user.id, req.trust_mode):
            yield event

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/batch")
async def start_batch_generation(
    project_id: str,
    req: BatchGenerateRequest = BatchGenerateRequest(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project(project_id, user, db)

    async def stream():
        async for event in generate_batch(
            db, project, user.id,
            start_chapter=req.start_chapter,
            trust_mode=req.trust_mode,
        ):
            yield event

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chapter/{chapter_no}")
async def start_chapter_regeneration(
    project_id: str,
    chapter_no: int,
    req: GenerateRequest = GenerateRequest(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project(project_id, user, db)

    async def stream():
        async for event in regenerate_chapter(
            db, project, user.id, chapter_no, req.trust_mode,
        ):
            yield event

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ─── Workflow State ─────────────────────────────────────

@router.get("/status", response_model=WorkflowStateResponse)
async def get_workflow_status(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, user, db)
    result = await db.execute(
        select(WorkflowStateRecord)
        .where(WorkflowStateRecord.project_id == project_id)
    )
    ws = result.scalar_one_or_none()
    if not ws:
        return WorkflowStateResponse(
            current_state="idle", current_chapter_no=0, pending_data="{}",
        )
    return WorkflowStateResponse(
        current_state=ws.current_state,
        current_chapter_no=ws.current_chapter_no,
        pending_data=ws.pending_data,
    )


# ─── Outline Confirm ───────────────────────────────────

@router.post("/outline/confirm")
async def confirm_outline(
    project_id: str,
    req: OutlineConfirmRequest = OutlineConfirmRequest(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project(project_id, user, db)

    if req.outline is not None:
        project.outline = req.outline

    project.status = "outline_confirmed"

    # Update workflow state
    result = await db.execute(
        select(WorkflowStateRecord)
        .where(WorkflowStateRecord.project_id == project_id)
    )
    ws = result.scalar_one_or_none()
    if ws:
        ws.current_state = "outline_confirmed"

    await db.commit()
    return {"status": "outline_confirmed"}


# ─── Export ─────────────────────────────────────────────

@router.get("/export/txt", response_model=ExportResponse)
async def export_txt(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await _get_project(project_id, user, db)

    result = await db.execute(
        select(Chapter)
        .where(Chapter.project_id == project_id)
        .order_by(Chapter.chapter_no)
    )
    chapters = result.scalars().all()

    if not chapters:
        raise HTTPException(status_code=400, detail="没有可导出的章节")

    lines = [f"《{project.title}》", ""]
    for ch in chapters:
        lines.append(f"第{ch.chapter_no}章 {ch.title}")
        lines.append("")
        lines.append(ch.content or "（未生成）")
        lines.append("")
        lines.append("")

    content = "\n".join(lines)
    filename = f"{project.title}.txt"

    return ExportResponse(filename=filename, content=content)
