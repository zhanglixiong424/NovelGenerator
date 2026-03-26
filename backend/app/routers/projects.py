from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models import User, NovelProject, Chapter, WorkflowStateRecord
from app.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ChapterResponse, ChapterUpdate, ChapterListItem,
)

router = APIRouter(prefix="/api", tags=["projects"])


# ─── Projects ──────────────────────────────────────────

@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NovelProject)
        .where(NovelProject.user_id == user.id)
        .order_by(NovelProject.updated_at.desc())
    )
    projects = result.scalars().all()
    responses = []
    for p in projects:
        count_result = await db.execute(
            select(func.count(Chapter.id)).where(Chapter.project_id == p.id)
        )
        responses.append(ProjectResponse(
            id=p.id, title=p.title, genre=p.genre,
            target_platform=p.target_platform,
            target_word_count=p.target_word_count,
            outline=p.outline, world_setting=p.world_setting,
            status=p.status,
            chapter_count=count_result.scalar() or 0,
            created_at=p.created_at, updated_at=p.updated_at,
        ))
    return responses


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    req: ProjectCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    project = NovelProject(
        user_id=user.id,
        title=req.title,
        genre=req.genre,
        target_platform=req.target_platform,
        target_word_count=req.target_word_count,
    )
    db.add(project)
    # Create initial workflow state
    ws = WorkflowStateRecord(project_id=project.id, current_state="idle")
    db.add(ws)
    await db.commit()
    await db.refresh(project)
    return ProjectResponse(
        id=project.id, title=project.title, genre=project.genre,
        target_platform=project.target_platform,
        target_word_count=project.target_word_count,
        outline=project.outline, world_setting=project.world_setting,
        status=project.status, chapter_count=0,
        created_at=project.created_at, updated_at=project.updated_at,
    )


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NovelProject).where(
            NovelProject.id == project_id,
            NovelProject.user_id == user.id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    count_result = await db.execute(
        select(func.count(Chapter.id)).where(Chapter.project_id == project.id)
    )
    return ProjectResponse(
        id=project.id, title=project.title, genre=project.genre,
        target_platform=project.target_platform,
        target_word_count=project.target_word_count,
        outline=project.outline, world_setting=project.world_setting,
        status=project.status,
        chapter_count=count_result.scalar() or 0,
        created_at=project.created_at, updated_at=project.updated_at,
    )


@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    req: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NovelProject).where(
            NovelProject.id == project_id,
            NovelProject.user_id == user.id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(project, k, v)

    await db.commit()
    await db.refresh(project)
    count_result = await db.execute(
        select(func.count(Chapter.id)).where(Chapter.project_id == project.id)
    )
    return ProjectResponse(
        id=project.id, title=project.title, genre=project.genre,
        target_platform=project.target_platform,
        target_word_count=project.target_word_count,
        outline=project.outline, world_setting=project.world_setting,
        status=project.status,
        chapter_count=count_result.scalar() or 0,
        created_at=project.created_at, updated_at=project.updated_at,
    )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NovelProject).where(
            NovelProject.id == project_id,
            NovelProject.user_id == user.id,
        )
    )
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(project)
    await db.commit()
    return {"message": "Deleted"}


# ─── Chapters ──────────────────────────────────────────

@router.get("/projects/{project_id}/chapters", response_model=list[ChapterListItem])
async def list_chapters(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify ownership
    proj = await db.execute(
        select(NovelProject.id).where(
            NovelProject.id == project_id,
            NovelProject.user_id == user.id,
        )
    )
    if proj.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(Chapter)
        .where(Chapter.project_id == project_id)
        .order_by(Chapter.chapter_no)
    )
    return [
        ChapterListItem(
            id=c.id, chapter_no=c.chapter_no, title=c.title,
            word_count=c.word_count, status=c.status,
            compliance_status=c.compliance_status,
            consistency_status=c.consistency_status,
        )
        for c in result.scalars().all()
    ]


@router.get("/chapters/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    chapter_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Chapter).join(NovelProject).where(
            Chapter.id == chapter_id,
            NovelProject.user_id == user.id,
        )
    )
    chapter = result.scalar_one_or_none()
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return ChapterResponse(
        id=chapter.id, chapter_no=chapter.chapter_no, title=chapter.title,
        outline=chapter.outline, content=chapter.content, summary=chapter.summary,
        word_count=chapter.word_count,
        compliance_status=chapter.compliance_status,
        consistency_status=chapter.consistency_status,
        status=chapter.status,
        created_at=chapter.created_at, updated_at=chapter.updated_at,
    )


@router.put("/chapters/{chapter_id}", response_model=ChapterResponse)
async def update_chapter(
    chapter_id: str,
    req: ChapterUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Chapter).join(NovelProject).where(
            Chapter.id == chapter_id,
            NovelProject.user_id == user.id,
        )
    )
    chapter = result.scalar_one_or_none()
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")

    for k, v in req.model_dump(exclude_unset=True).items():
        setattr(chapter, k, v)
    if req.content is not None:
        chapter.word_count = len(req.content)

    await db.commit()
    await db.refresh(chapter)
    return ChapterResponse(
        id=chapter.id, chapter_no=chapter.chapter_no, title=chapter.title,
        outline=chapter.outline, content=chapter.content, summary=chapter.summary,
        word_count=chapter.word_count,
        compliance_status=chapter.compliance_status,
        consistency_status=chapter.consistency_status,
        status=chapter.status,
        created_at=chapter.created_at, updated_at=chapter.updated_at,
    )


@router.delete("/chapters/{chapter_id}")
async def delete_chapter(
    chapter_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Chapter).join(NovelProject).where(
            Chapter.id == chapter_id,
            NovelProject.user_id == user.id,
        )
    )
    chapter = result.scalar_one_or_none()
    if chapter is None:
        raise HTTPException(status_code=404, detail="Chapter not found")
    await db.delete(chapter)
    await db.commit()
    return {"message": "Deleted"}
