import io
import zipfile

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.database import create_page, list_pages, get_page, rename_page, delete_page, get_page_generations
from app.models import CreatePageRequest, RenamePageRequest, PageResponse
from app.routes.auth import get_current_user
from app.storage import IMAGES_DIR

router = APIRouter()


@router.post("/pages", response_model=PageResponse)
async def create_new_page(req: CreatePageRequest, current_user=Depends(get_current_user)):
    page = create_page(req.title, user_id=current_user["id"])
    return page


@router.get("/pages", response_model=list[PageResponse])
async def get_pages(current_user=Depends(get_current_user)):
    return list_pages(user_id=current_user["id"])


@router.get("/pages/{page_id}/generations")
async def get_generations(page_id: int, current_user=Depends(get_current_user)):
    page = get_page(page_id)
    if not page or page.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다.")
    gens = get_page_generations(page_id)
    return [
        {
            "prompt_id": g["prompt_id"],
            "prompt_text": g["prompt_text"],
            "image_paths": g["image_paths"],
            "status": g.get("status", "done"),
            "error_msg": g.get("error_msg"),
        }
        for g in gens
    ]


@router.patch("/pages/{page_id}", response_model=PageResponse)
async def update_page_title(page_id: int, req: RenamePageRequest, current_user=Depends(get_current_user)):
    page = get_page(page_id)
    if not page or page.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다.")
    rename_page(page_id, req.title)
    return get_page(page_id)


@router.get("/pages/{page_id}/download-zip")
async def download_page_zip(page_id: int, current_user=Depends(get_current_user)):
    page = get_page(page_id)
    if not page or page.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다.")

    gens = get_page_generations(page_id)
    done = [g for g in gens if g.get("status", "done") == "done" and g["image_paths"]]

    if not done:
        raise HTTPException(status_code=404, detail="다운로드할 이미지가 없습니다.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for g in done:
            for path in g["image_paths"]:
                # path 형식: "images/{prompt_id}/{idx}.png"
                abs_path = IMAGES_DIR.parent / path
                if abs_path.exists():
                    zf.write(abs_path, path)

    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="carbatch-page-{page_id}.zip"'},
    )


@router.delete("/pages/{page_id}")
async def remove_page(page_id: int, current_user=Depends(get_current_user)):
    page = get_page(page_id)
    if not page or page.get("user_id") != current_user["id"]:
        raise HTTPException(status_code=404, detail="페이지를 찾을 수 없습니다.")
    delete_page(page_id)
    return {"ok": True}
