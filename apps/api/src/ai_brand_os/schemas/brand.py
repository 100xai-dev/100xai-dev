from pydantic import BaseModel, HttpUrl


class BrandCreate(BaseModel):
    name: str
    website: HttpUrl
    industry: str | None = None
    manual_notes: str | None = None


class BrandRead(BaseModel):
    id: str
    name: str
    website: HttpUrl
    industry: str | None
    status: str

