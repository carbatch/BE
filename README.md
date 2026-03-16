# Batch Image Studio — AI Backend

Pollinations.ai를 이용한 이미지 생성 FastAPI 백엔드입니다.  
**API 키 불필요 · 완전 무료 · 검열 최소화**

---

## 폴더 구조

```
AI/
├── main.py           # FastAPI 앱 (메인 진입점)
├── requirements.txt  # Python 패키지 목록
├── .env.example      # 환경변수 예시 (복사 후 .env로 사용)
└── README.md
```

---

## 시작하기

### 1. Python 가상환경 생성 및 활성화

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 열고 필요한 값 수정
```

### 4. 서버 실행

```bash
uvicorn main:app --port 8080
```

서버가 `http://localhost:8080` 에서 시작됩니다.

---

## API 명세

### `POST /api/v1/generate`

이미지를 생성하고 Base64 Data URL 배열로 반환합니다.

**Request Body**
```json
{
  "prompt": "Medium shot, a Korean boy standing in moonlight, cinematic",
  "id": "001",
  "count": 1
}
```

**Response (200 OK)**
```json
{
  "images": [
    "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAA..."
  ]
}
```

### `GET /health`

서버 상태 확인.

---

## 환경변수 설명

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `PORT` | `8080` | 서버 포트 |
| `IMAGE_WIDTH` | `1344` | 생성 이미지 가로 (px) |
| `IMAGE_HEIGHT` | `768` | 생성 이미지 세로 (px, 16:9 비율) |
| `IMAGE_MODEL` | `flux` | Pollinations 모델 (`flux` or `turbo`) |
| `TIMEOUT_SECONDS` | `60` | 이미지 생성 타임아웃 (초) |
| `ALLOWED_ORIGINS` | `*` | CORS 허용 Origin |

---

## FE 연동

프론트엔드 `FE/` 폴더에 `.env.local` 파일을 생성하고 아래 내용을 추가하세요.

```env
NEXT_PUBLIC_API_URL=http://localhost:8080/api/v1/generate
```

---

## Pollinations.ai 모델 선택

| 모델 | 속도 | 품질 | 특징 |
|------|------|------|------|
| `flux` | 느림 (10~20초) | ⭐⭐⭐⭐⭐ | 고품질, 세밀한 묘사 |
| `turbo` | 빠름 (3~8초) | ⭐⭐⭐ | 빠른 프리뷰용 |

`.env`의 `IMAGE_MODEL` 값을 바꿔 모델을 전환할 수 있습니다.
