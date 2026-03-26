from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.auth import get_current_user
from app.database import get_db
from app.encryption import encrypt_api_key, decrypt_api_key, mask_api_key
from app.models import User, AIProviderConfig
from app.schemas import (
    AIProviderCreate, AIProviderUpdate, AIProviderResponse, AIProviderTestResult,
)

router = APIRouter(prefix="/api/settings/ai", tags=["ai-config"])


def _to_response(cfg: AIProviderConfig) -> AIProviderResponse:
    try:
        raw_key = decrypt_api_key(cfg.api_key_encrypted)
        masked = mask_api_key(raw_key)
    except Exception:
        masked = "***"
    return AIProviderResponse(
        id=cfg.id,
        name=cfg.name,
        provider_type=cfg.provider_type,
        api_key_masked=masked,
        base_url=cfg.base_url,
        model_name=cfg.model_name,
        priority=cfg.priority,
        is_enabled=cfg.is_enabled,
        max_tokens=cfg.max_tokens,
        temperature=cfg.temperature,
        last_test_status=cfg.last_test_status,
        last_test_at=cfg.last_test_at,
        created_at=cfg.created_at,
        updated_at=cfg.updated_at,
    )


@router.get("", response_model=list[AIProviderResponse])
async def list_configs(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIProviderConfig)
        .where(AIProviderConfig.user_id == user.id)
        .order_by(AIProviderConfig.priority)
    )
    return [_to_response(c) for c in result.scalars().all()]


@router.post("", response_model=AIProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    req: AIProviderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cfg = AIProviderConfig(
        user_id=user.id,
        name=req.name,
        provider_type=req.provider_type,
        api_key_encrypted=encrypt_api_key(req.api_key),
        base_url=req.base_url,
        model_name=req.model_name,
        priority=req.priority,
        is_enabled=req.is_enabled,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
    )
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return _to_response(cfg)


@router.put("/{config_id}", response_model=AIProviderResponse)
async def update_config(
    config_id: str,
    req: AIProviderUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIProviderConfig).where(
            AIProviderConfig.id == config_id,
            AIProviderConfig.user_id == user.id,
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Config not found")

    update_data = req.model_dump(exclude_unset=True)
    if "api_key" in update_data:
        cfg.api_key_encrypted = encrypt_api_key(update_data.pop("api_key"))
    for k, v in update_data.items():
        setattr(cfg, k, v)

    await db.commit()
    await db.refresh(cfg)
    return _to_response(cfg)


@router.delete("/{config_id}")
async def delete_config(
    config_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIProviderConfig).where(
            AIProviderConfig.id == config_id,
            AIProviderConfig.user_id == user.id,
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Config not found")
    await db.delete(cfg)
    await db.commit()
    return {"message": "Deleted"}


@router.post("/{config_id}/test", response_model=AIProviderTestResult)
async def test_config(
    config_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AIProviderConfig).where(
            AIProviderConfig.id == config_id,
            AIProviderConfig.user_id == user.id,
        )
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        raise HTTPException(status_code=404, detail="Config not found")

    api_key = decrypt_api_key(cfg.api_key_encrypted)
    start = datetime.now(timezone.utc)

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            url = cfg.base_url.rstrip("/") + "/chat/completions"
            resp = await client.post(
                url,
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": cfg.model_name,
                    "messages": [{"role": "user", "content": "Hi"}],
                    "max_tokens": 5,
                },
            )
            latency = int((datetime.now(timezone.utc) - start).total_seconds() * 1000)

            if resp.status_code == 200:
                cfg.last_test_status = "success"
                cfg.last_test_at = datetime.now(timezone.utc)
                await db.commit()
                return AIProviderTestResult(success=True, message="连通成功", latency_ms=latency)
            else:
                cfg.last_test_status = "failed"
                cfg.last_test_at = datetime.now(timezone.utc)
                await db.commit()
                return AIProviderTestResult(
                    success=False,
                    message=f"HTTP {resp.status_code}: {resp.text[:200]}",
                    latency_ms=latency,
                )
    except httpx.TimeoutException:
        cfg.last_test_status = "failed"
        cfg.last_test_at = datetime.now(timezone.utc)
        await db.commit()
        return AIProviderTestResult(success=False, message="连接超时")
    except Exception as e:
        cfg.last_test_status = "failed"
        cfg.last_test_at = datetime.now(timezone.utc)
        await db.commit()
        return AIProviderTestResult(success=False, message=str(e)[:200])
