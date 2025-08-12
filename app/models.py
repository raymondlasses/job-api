from pydantic import BaseModel, HttpUrl

class OSRequest(BaseModel):
    command: str

class KatanaRequest(BaseModel):
    url: HttpUrl
