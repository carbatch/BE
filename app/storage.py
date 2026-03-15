import base64
from pathlib import Path

IMAGES_DIR = Path(__file__).parent.parent / "storage" / "images"


def save_images(prompt_id: str, data_urls: list[str]) -> list[str]:
    """
    Base64 data URI 목록을 PNG 파일로 저장하고 상대 경로 목록 반환.
    반환값: ["images/{prompt_id}/1.png", ...]  → StaticFiles 기준 경로
    """
    folder = IMAGES_DIR / prompt_id
    folder.mkdir(parents=True, exist_ok=True)

    paths: list[str] = []
    for idx, data_url in enumerate(data_urls, start=1):
        try:
            _, b64 = data_url.split(",", 1)
            img_bytes = base64.b64decode(b64)
            file_path = folder / f"{idx}.png"
            file_path.write_bytes(img_bytes)
            paths.append(f"images/{prompt_id}/{idx}.png")
        except Exception as e:
            print(f"[storage] {prompt_id}/{idx} 저장 실패: {e}")

    return paths
