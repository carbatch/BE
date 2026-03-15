import asyncio

from fastapi import APIRouter, HTTPException

from app.config import openai_client, IMAGE_MODEL
from app.database import (
    create_generation_pending,
    update_generation_running,
    update_generation_done,
    update_generation_error,
    get_generation_by_prompt_id,
)
from app.models import GenerateRequest, GenerateAsyncResponse, GenerationStatusResponse
from app.storage import save_images

router = APIRouter()

# 백그라운드 태스크 GC 방지용 참조 보관
_bg_tasks: set[asyncio.Task] = set()


@router.post("/generate", response_model=GenerateAsyncResponse)
async def generate_images(req: GenerateRequest):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt 필드가 비어있습니다.")

    count = max(1, min(req.count, 4))
    create_generation_pending(req.id, req.prompt, "dall-e", req.page_id, count)
    print(f"[{req.id}] OpenAI 백그라운드 요청 — count={count}, prompt={req.prompt[:80]}...")

    task = asyncio.create_task(_generate_task(req.id, req.prompt, count))
    _bg_tasks.add(task)
    task.add_done_callback(_bg_tasks.discard)

    return GenerateAsyncResponse(prompt_id=req.id, status="pending")


@router.get("/generations/{prompt_id}/status", response_model=GenerationStatusResponse)
async def get_generation_status(prompt_id: str):
    gen = get_generation_by_prompt_id(prompt_id)
    if not gen:
        raise HTTPException(status_code=404, detail="생성 기록을 찾을 수 없습니다.")
    return GenerationStatusResponse(
        prompt_id=prompt_id,
        status=gen["status"],
        image_paths=gen["image_paths"],
        error_msg=gen.get("error_msg"),
    )


async def _generate_task(prompt_id: str, prompt: str, count: int):
    update_generation_running(prompt_id)
    images: list[str] = []
    last_error: str | None = None

    for i in range(count):
        try:
            response = await openai_client.images.generate(
                model=IMAGE_MODEL,
                prompt=prompt,
                size="1024x1024",
                quality="standard",
                n=1,
                response_format="b64_json",
            )
            image_b64 = response.data[0].b64_json
            images.append(f"data:image/png;base64,{image_b64}")
            print(f"[{prompt_id}] {i+1}/{count} 완료")
        except Exception as e:
            last_error = str(e)
            print(f"[{prompt_id}] {i+1}/{count} 실패: {last_error}")

        if i < count - 1:
            await asyncio.sleep(1)

    if images:
        saved_paths = save_images(prompt_id, images)
        update_generation_done(prompt_id, saved_paths)
        print(f"[{prompt_id}] 완료 — {len(images)}장 저장")
    else:
        update_generation_error(prompt_id, last_error or "이미지 생성 실패")
        print(f"[{prompt_id}] 실패: {last_error}")
