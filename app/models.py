from pydantic import BaseModel


class GenerateRequest(BaseModel):
    prompt: str
    id: str = "000"
    count: int = 1


class GenerateResponse(BaseModel):
    images: list[str]
