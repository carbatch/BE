from dotenv import load_dotenv
load_dotenv()

import os
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import ALLOWED_ORIGINS
from app.database import init_db
from app.routes import openai as openai_router
from app.routes import pollinations as pollinations_router
from app.routes import style as style_router
from app.routes import history as history_router
from app.routes import pages as pages_router

app = FastAPI(title="Batch Image Studio AI Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pollinations_router.router, prefix="/api/v1")
app.include_router(openai_router.router, prefix="/api/v1")
app.include_router(style_router.router, prefix="/api/v1")
app.include_router(history_router.router, prefix="/api/v1")
app.include_router(pages_router.router, prefix="/api/v1")

# DB 초기화 및 정적 파일 서빙
init_db()
_storage_images = Path(__file__).parent / "storage" / "images"
_storage_images.mkdir(parents=True, exist_ok=True)
app.mount("/storage/images", StaticFiles(directory=str(_storage_images)), name="images")


@app.get("/")
async def root():
    return {"status": "ok", "service": "Batch Image Studio AI Backend"}


@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn
    import socket

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8081))

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("localhost", port)) == 0:
            print(f"❌ 오류: {port} 포트가 이미 사용 중입니다.")
            exit(1)

    print(f"\n🚀 AI Backend 가 구동됩니다: http://{host if host != '0.0.0.0' else '100.96.206.122'}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
