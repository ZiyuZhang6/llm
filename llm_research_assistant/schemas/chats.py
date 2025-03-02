from pydantic import BaseModel
from typing import List, Any, Optional


class ChatBase(BaseModel):
    owner_id: str
    # We can store messages as an array of objects. Example:
    # [{ "role": "user", "content": "Hello" }, ...]
    message_chain: List[Any] = []


class ChatCreate(ChatBase):
    pass


class ChatUpdate(BaseModel):
    message_chain: Optional[List[Any]] = None


class ChatResponse(ChatBase):
    id: str

    class Config:
        orm_mode = True
