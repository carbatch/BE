"""
Batch Image Studio — AI Backend
이미지 생성: Pollinations.ai (무료, API 키 불필요)

★ 동작 방식:
  서버에서 Pollinations URL로 이미지를 직접 받아(Base64) FE에 반환합니다.
  User-Agent 헤더 및 재시도 로직으로 502 오류를 방지합니다.
"""

import os
import urllib.parse
import time
import random
import base64

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Batch Image Studio AI Backend", version="1.0.0")

# ── CORS 설정 ─────────────────────────────────────────────
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Pollinations 설정 ─────────────────────────────────────
POLLINATIONS_BASE = "https://image.pollinations.ai/prompt"
DEFAULT_WIDTH    = int(os.getenv("IMAGE_WIDTH",  "1344"))
DEFAULT_HEIGHT   = int(os.getenv("IMAGE_HEIGHT", "768"))   # 16:9
DEFAULT_MODEL    = os.getenv("IMAGE_MODEL", "flux")        # flux | turbo
TIMEOUT_SECONDS  = float(os.getenv("TIMEOUT_SECONDS", "90"))
MAX_RETRIES      = int(os.getenv("MAX_RETRIES", "2"))

# Pollinations이 봇 차단을 하는 경우가 있으므로 브라우저 UA를 사용
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
    "Referer": "https://pollinations.ai/",
}


# ── 요청/응답 모델 ─────────────────────────────────────────
class GenerateRequest(BaseModel):
    prompt: str
    id: str = "000"
    count: int = 1


class GenerateResponse(BaseModel):
    images: list[str]


# ── 유틸리티 ──────────────────────────────────────────────
def build_pollinations_url(prompt: str, seed: int) -> str:
    encoded = urllib.parse.quote(prompt, safe="")
    params = (
        f"width={DEFAULT_WIDTH}"
        f"&height={DEFAULT_HEIGHT}"
        f"&model={DEFAULT_MODEL}"
        f"&seed={seed}"
        f"&nologo=true"
        f"&nofeed=true"
        f"&enhance=false"
    )
    return f"{POLLINATIONS_BASE}/{encoded}?{params}"


async def download_image_as_base64(url: str) -> str:
    """
    Pollinations URL에서 이미지 바이너리를 받아 Base64 Data URL로 반환합니다.
    실패 시 MAX_RETRIES 횟수만큼 다른 seed로 재시도합니다.
    """
    async with httpx.AsyncClient(
        timeout=httpx.Timeout(TIMEOUT_SECONDS),
        follow_redirects=True,
        headers=REQUEST_HEADERS,
    ) as client:
        resp = await client.get(url)
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "image/jpeg")
        if not content_type.startswith("image/"):
            raise ValueError(f"이미지가 아닌 응답: {content_type} (url={url[:80]})")

        b64 = base64.b64encode(resp.content).decode("utf-8")
        return f"data:{content_type};base64,{b64}"


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
    프롬프트를 받아 Pollinations.ai로 이미지를 생성하고,
    Base64 Data URL 목록을 FE에 반환합니다.
    """
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt 필드가 비어있습니다.")

    count = max(1, min(req.count, 4))
    print(f"[{req.id}] 요청 — count={count}, prompt={req.prompt[:80]}...")

    images: list[str] = []
    base_seed = random.randint(1, 900000)

    for i in range(count):
        data_url = None
        last_error = None

        # 실패 시 다른 seed로 재시도
        for attempt in range(MAX_RETRIES + 1):
            seed = base_seed + i + (attempt * 1000)
            url = build_pollinations_url(req.prompt, seed)
            try:
                data_url = await download_image_as_base64(url)
                print(f"[{req.id}] {i+1}/{count} 완료 (시도 {attempt+1})")
                break
            except httpx.TimeoutException as e:
                last_error = f"타임아웃 ({TIMEOUT_SECONDS}s)"
                print(f"[{req.id}] {i+1}/{count} 시도 {attempt+1} 타임아웃")
            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}"
                print(f"[{req.id}] {i+1}/{count} 시도 {attempt+1} HTTP 오류: {e.response.status_code}")
            except Exception as e:
                last_error = str(e)
                print(f"[{req.id}] {i+1}/{count} 시도 {attempt+1} 예외: {e}")

        if data_url:
            images.append(data_url)
        else:
            # 한 장 실패해도 나머지는 계속 시도 (FE에서 에러 카드로 표시)
            print(f"[{req.id}] {i+1}/{count} 최종 실패: {last_error}")

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
║   모델: {DEFAULT_MODEL:<10}  크기: {DEFAULT_WIDTH}x{DEFAULT_HEIGHT}       ║
║   타임아웃: {TIMEOUT_SECONDS}s   재시도: {MAX_RETRIES}회              ║
╚══════════════════════════════════════════════╝
""")
    # app 객체를 직접 전달하면 중복 로드 및 포트 바인딩 오류 가능성이 줄어듭니다.
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
