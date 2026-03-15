from fastapi import APIRouter, HTTPException

from app.database import get_history, get_generation

router = APIRouter()


@router.get("/history")
async def list_history(limit: int = 50, offset: int = 0):
    """생성 이력 목록 조회"""
    return get_history(limit=limit, offset=offset)


@router.get("/history/{generation_id}")
async def get_one(generation_id: int):
    """특정 생성 이력 단건 조회"""
    record = get_generation(generation_id)
    if not record:
        raise HTTPException(status_code=404, detail="해당 이력을 찾을 수 없습니다.")
    return record
