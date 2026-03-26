"""Knowledge base API endpoints."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import (
    User, NovelProject, KnowledgeEntity, KnowledgeVersion,
    KnowledgeChange,
)
from app.schemas import (
    KnowledgeEntityResponse, KnowledgeEntityUpdate,
    KnowledgeVersionResponse, KnowledgeChangeResponse,
    KnowledgeConfirmRequest,
)

router = APIRouter(prefix="/api/projects/{project_id}/knowledge", tags=["knowledge"])


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


# ─── Entity CRUD ────────────────────────────────────────

@router.get("", response_model=list[KnowledgeEntityResponse])
async def list_entities(
    project_id: str,
    entity_type: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, user, db)
    query = select(KnowledgeEntity).where(KnowledgeEntity.project_id == project_id)
    if entity_type:
        query = query.where(KnowledgeEntity.entity_type == entity_type)
    query = query.order_by(KnowledgeEntity.entity_type, KnowledgeEntity.name)
    result = await db.execute(query)
    return [KnowledgeEntityResponse(
        id=e.id, entity_type=e.entity_type, name=e.name,
        data=e.data, summary=e.summary, is_important=e.is_important,
        first_appearance=e.first_appearance,
        created_at=e.created_at, updated_at=e.updated_at,
    ) for e in result.scalars().all()]


@router.get("/{entity_id}", response_model=KnowledgeEntityResponse)
async def get_entity(
    project_id: str, entity_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, user, db)
    result = await db.execute(
        select(KnowledgeEntity).where(
            KnowledgeEntity.id == entity_id,
            KnowledgeEntity.project_id == project_id,
        )
    )
    e = result.scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Entity not found")
    return KnowledgeEntityResponse(
        id=e.id, entity_type=e.entity_type, name=e.name,
        data=e.data, summary=e.summary, is_important=e.is_important,
        first_appearance=e.first_appearance,
        created_at=e.created_at, updated_at=e.updated_at,
    )


@router.put("/{entity_id}", response_model=KnowledgeEntityResponse)
async def update_entity(
    project_id: str, entity_id: str,
    req: KnowledgeEntityUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, user, db)
    result = await db.execute(
        select(KnowledgeEntity).where(
            KnowledgeEntity.id == entity_id,
            KnowledgeEntity.project_id == project_id,
        )
    )
    e = result.scalar_one_or_none()
    if not e:
        raise HTTPException(status_code=404, detail="Entity not found")

    update_data = req.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(e, k, v)
    await db.commit()
    await db.refresh(e)

    return KnowledgeEntityResponse(
        id=e.id, entity_type=e.entity_type, name=e.name,
        data=e.data, summary=e.summary, is_important=e.is_important,
        first_appearance=e.first_appearance,
        created_at=e.created_at, updated_at=e.updated_at,
    )


# ─── Versions & Changes ────────────────────────────────

@router.get("/versions", response_model=list[KnowledgeVersionResponse])
async def list_versions(
    project_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, user, db)
    result = await db.execute(
        select(KnowledgeVersion)
        .where(KnowledgeVersion.project_id == project_id)
        .options(selectinload(KnowledgeVersion.changes))
        .order_by(KnowledgeVersion.version_no.desc())
        .limit(50)
    )
    versions = result.scalars().all()
    return [KnowledgeVersionResponse(
        id=v.id, version_no=v.version_no, chapter_no=v.chapter_no,
        created_at=v.created_at,
        changes=[KnowledgeChangeResponse(
            id=c.id, entity_type=c.entity_type, entity_id=c.entity_id,
            field=c.field, old_value=c.old_value, new_value=c.new_value,
            is_auto_extracted=c.is_auto_extracted, is_confirmed=c.is_confirmed,
            created_at=c.created_at,
        ) for c in v.changes],
    ) for v in versions]


# ─── Confirm Knowledge Changes ─────────────────────────

@router.post("/confirm")
async def confirm_changes(
    project_id: str,
    req: KnowledgeConfirmRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _get_project(project_id, user, db)

    # Get the version
    result = await db.execute(
        select(KnowledgeVersion)
        .where(
            KnowledgeVersion.id == req.version_id,
            KnowledgeVersion.project_id == project_id,
        )
        .options(selectinload(KnowledgeVersion.changes))
    )
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    confirmed_count = 0
    changes_to_apply = []

    for change in version.changes:
        if req.confirm_all or change.id in req.confirmed_change_ids:
            change.is_confirmed = True
            confirmed_count += 1
            changes_to_apply.append({
                "entity_type": change.entity_type,
                "name": change.entity_id,
                "field": change.field,
                "old_value": change.old_value,
                "new_value": change.new_value,
            })

    await db.commit()

    # Apply confirmed changes to knowledge entities
    if changes_to_apply:
        await _apply_changes_to_entities(db, project_id, changes_to_apply)

    return {"confirmed": confirmed_count, "total": len(version.changes)}


async def _apply_changes_to_entities(
    db: AsyncSession, project_id: str, changes: list[dict],
):
    """Apply confirmed changes to knowledge entities."""
    for ch in changes:
        entity_type = ch.get("entity_type", "")
        name = ch.get("name", "")
        if not entity_type or not name:
            continue

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
                summary="",
            )
            db.add(entity)
            await db.flush()

        try:
            data = json.loads(entity.data) if entity.data else {}
        except json.JSONDecodeError:
            data = {}

        field = ch.get("field", "")
        if field:
            # Try to parse new_value as JSON first, fall back to string
            new_val = ch.get("new_value", "")
            try:
                new_val = json.loads(new_val)
            except (json.JSONDecodeError, TypeError):
                pass
            data[field] = new_val
            entity.data = json.dumps(data, ensure_ascii=False)

    await db.commit()
