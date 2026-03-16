from fastapi import APIRouter, Depends, HTTPException

from app.config import openai_client
from app.models import ExtractStyleRequest, ExtractStyleResponse
from app.routes.auth import get_current_user

router = APIRouter()

STYLE_EXTRACTION_PROMPT = (
    "Analyze the visual style of this image and describe it as a concise image generation prompt. "
    "Focus on: lighting, color palette, art style, mood, texture, and rendering technique. "
    "Output only the style descriptor string, no explanation. "
    "Example: 'warm cinematic lighting, oil painting style, golden hour, rich earthy tones, soft bokeh'"
)


@router.post("/extract-style", response_model=ExtractStyleResponse)
async def extract_style(req: ExtractStyleRequest, _=Depends(get_current_user)):
    if not req.image or not req.image.strip():
        raise HTTPException(status_code=400, detail="image 필드가 비어있습니다.")

    if not req.image.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="올바른 이미지 데이터 URI 형식이 아닙니다. (data:image/...;base64,...)")

    try:
        header, b64_data = req.image.split(",", 1)
        mime_type = header.split(";")[0].replace("data:", "")  # e.g., "image/png"
    except ValueError:
        raise HTTPException(status_code=400, detail="이미지 데이터 URI 파싱에 실패했습니다.")

    print(f"[extract-style] 스타일 추출 요청 — mime={mime_type}, size={len(b64_data)} chars")

    try:
        response = await openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": req.image,
                                "detail": "low",
                            },
                        },
                        {
                            "type": "text",
                            "text": STYLE_EXTRACTION_PROMPT,
                        },
                    ],
                }
            ],
            max_tokens=200,
        )

        style_text = response.choices[0].message.content.strip()
        print(f"[extract-style] 추출 완료: {style_text}")
        return ExtractStyleResponse(style=style_text)

    except Exception as e:
        print(f"[extract-style] 오류: {e}")
        raise HTTPException(status_code=502, detail=f"스타일 추출 실패: {str(e)}")
