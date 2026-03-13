import asyncio
import base64
import random
import urllib.parse

import httpx
from fastapi import APIRouter, HTTPException

from app.config import POLLINATIONS_MODEL
from app.models import GenerateRequest, GenerateResponse

router = APIRouter()

POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"
MAX_RETRIES = 2
TIMEOUT = 60.0


@router.post("/generate", response_model=GenerateResponse)
async def generate_images_free(req: GenerateRequest):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt 필드가 비어있습니다.")

    count = max(1, min(req.count, 4))
    print(f"[{req.id}] Pollinations 요청 — count={count}, prompt={req.prompt[:80]}...")

    images: list[str] = []

    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        for i in range(count):
            data_url = await _fetch_image(client, req.prompt, req.id, i + 1, count)
            if data_url:
                images.append(data_url)
            if i < count - 1:
                await asyncio.sleep(0.5)

    if not images:
        raise HTTPException(status_code=502, detail="Pollinations 서버에서 이미지를 생성하지 못했습니다.")

    return GenerateResponse(images=images)


async def _fetch_image(
    client: httpx.AsyncClient, prompt: str, req_id: str, idx: int, total: int
) -> str | None:
    encoded = urllib.parse.quote(prompt)
    seed = random.randint(0, 999999)
    url = f"{POLLINATIONS_BASE}/{encoded}?model={POLLINATIONS_MODEL}&seed={seed}&nologo=true&width=1024&height=1024"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = await client.get(url)
            if response.status_code == 200:
                b64 = base64.b64encode(response.content).decode("utf-8")
                print(f"[{req_id}] {idx}/{total} 완료 (시도 {attempt})")
                return f"data:image/png;base64,{b64}"
            print(f"[{req_id}] {idx}/{total} 재시도 {attempt}/{MAX_RETRIES} — HTTP {response.status_code}")
        except Exception as e:
            print(f"[{req_id}] {idx}/{total} 재시도 {attempt}/{MAX_RETRIES} — {e}")

        if attempt < MAX_RETRIES:
            await asyncio.sleep(2 * attempt)

    print(f"[{req_id}] {idx}/{total} Pollinations 실패, Picsum으로 대체합니다.")
    try:
        url_fallback = f"https://picsum.photos/seed/{seed}/1024/1024"
        response = await client.get(url_fallback)
        if response.status_code == 200:
            b64 = base64.b64encode(response.content).decode("utf-8")
            return f"data:image/png;base64,{b64}"
    except Exception as e:
        print(f"[{req_id}] {idx}/{total} Picsum 대체 실패 — {e}")

    return None
