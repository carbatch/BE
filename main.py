"""
Batch Image Studio — AI Backend
이미지 생성: OpenAI DALL-E 3 (API Key 필요)

★ 동작 방식:
  서버에서 OpenAI API를 사용하여 Base64Data 형태로 이미지를 받아 FE에 반환합니다.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import asyncio
import time
import random

from openai import AsyncOpenAI, RateLimitError, APIError, APIConnectionError
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Batch Image Studio AI Backend", version="1.1.0")

# ── CORS 설정 ─────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── OpenAI 설정 ─────────────────────────────────────
DEFAULT_MODEL    = os.getenv("IMAGE_MODEL", "dall-e-3")
TIMEOUT_SECONDS  = float(os.getenv("TIMEOUT_SECONDS", "120"))
MAX_RETRIES      = int(os.getenv("MAX_RETRIES", "4"))
RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "5"))

client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    timeout=TIMEOUT_SECONDS
)

# ── 요청/응답 모델 ─────────────────────────────────────────
class GenerateRequest(BaseModel):
    prompt: str
    id: str = "000"
    count: int = 1

class GenerateResponse(BaseModel):
    images: list[str]

# ── 엔드포인트 ─────────────────────────────────────────────
@app.get("/")
async def root():
    return {"status": "ok", "service": "Batch Image Studio AI Backend"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}


@app.post("/api/v1/generate", response_model=GenerateResponse)
async def generate_images(req: GenerateRequest):
    """
    프롬프트를 받아 OpenAI DALL-E 3로 이미지를 생성하고,
    Base64 Data URL 목록을 FE에 반환합니다.
    """
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt 필드가 비어있습니다.")

    count = max(1, min(req.count, 4))
    print(f"[{req.id}] 요청 — count={count}, prompt={req.prompt[:80]}...")

    images: list[str] = []

    for i in range(count):
        data_url: str | None = None
        last_error: str | None = None

        try:
            response = await client.images.generate(
                model=DEFAULT_MODEL,
                prompt=req.prompt,
                size="1024x1024",
                quality="standard",
                n=1,
                response_format="b64_json"
            )
            image_b64 = response.data[0].b64_json
            data_url = f"data:image/png;base64,{image_b64}"
            print(f"[{req.id}] {i+1}/{count} 완료")
            images.append(data_url)
        except Exception as e:
            last_error = str(e)
            print(f"[{req.id}] {i+1}/{count} 최종 실패: {last_error}")

        if i < count - 1:
            await asyncio.sleep(1)

    if not images:
        raise HTTPException(
            status_code=502,
            detail=f"이미지를 생성하지 못했습니다: {last_error}"
        )

    return GenerateResponse(images=images)


# ── 로컬 실행 ─────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    import socket

    port = int(os.getenv("PORT", 8080))
    
    # 포트 점유 확인
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(('localhost', port)) == 0:
            print(f"❌ 오류: {port} 포트가 이미 사용 중입니다.")
            print(f"   다른 프로세스가 종료될 때까지 기다리거나 .env에서 PORT를 변경하세요.")
            exit(1)

    print(f"""
╔══════════════════════════════════════════════╗
║   Batch Image Studio — AI Backend            ║
║   http://localhost:{port}                      ║
║   모델: {DEFAULT_MODEL:<10}                         ║
║   타임아웃: {TIMEOUT_SECONDS}s   재시도: {MAX_RETRIES}회              ║
║   재시도 딜레이: {RETRY_BASE_DELAY}초 (지수 백오프)         ║
╚══════════════════════════════════════════════╝
""")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
