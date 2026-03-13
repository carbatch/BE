import asyncio

from fastapi import APIRouter, HTTPException

from app.config import openai_client, IMAGE_MODEL
from app.models import GenerateRequest, GenerateResponse

router = APIRouter()


@router.post("/generate-dalle", response_model=GenerateResponse)
async def generate_images(req: GenerateRequest):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt 필드가 비어있습니다.")

    count = max(1, min(req.count, 4))
    print(f"[{req.id}] OpenAI 요청 — count={count}, prompt={req.prompt[:80]}...")

    images: list[str] = []
    last_error: str | None = None

    for i in range(count):
        try:
            response = await openai_client.images.generate(
                model=IMAGE_MODEL,
                prompt=req.prompt,
                size="1024x1024",
                quality="standard",
                n=1,
                response_format="b64_json",
            )
            image_b64 = response.data[0].b64_json
            images.append(f"data:image/png;base64,{image_b64}")
            print(f"[{req.id}] {i+1}/{count} 완료")
        except Exception as e:
            last_error = str(e)
            print(f"[{req.id}] {i+1}/{count} 실패: {last_error}")

        if i < count - 1:
            await asyncio.sleep(1)

    if not images:
        raise HTTPException(status_code=502, detail=f"이미지를 생성하지 못했습니다: {last_error}")

    return GenerateResponse(images=images)
