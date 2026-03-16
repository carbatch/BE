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
# .env 파일을 열고

OPENAI_API_KEY = "OPENAI_API 키 추가"
```

### 4. 서버 실행

```bash
uvicorn main:app --port 8080
```

서버가 `http://localhost:8080` 에서 시작됩니다.

---
