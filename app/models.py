from pydantic import BaseModel


class GenerateRequest(BaseModel):
    prompt: str
    id: str = "000"
    count: int = 1
    page_id: int | None = None


class GenerateResponse(BaseModel):
    images: list[str]


class GenerateAsyncResponse(BaseModel):
    prompt_id: str
    status: str


class GenerationStatusResponse(BaseModel):
    prompt_id: str
    status: str
    image_paths: list[str]
    error_msg: str | None = None


class ExtractStyleRequest(BaseModel):
    image: str


class ExtractStyleResponse(BaseModel):
    style: str


class CreatePageRequest(BaseModel):
    title: str = "새 채팅"


class RenamePageRequest(BaseModel):
    title: str


class PageResponse(BaseModel):
    id: int
    title: str
    created_at: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
