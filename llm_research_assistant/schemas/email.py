from typing import Optional
from pydantic import BaseModel, EmailStr


class EmailConnectRequest(BaseModel):
    email: str


class EmailFetchResponse(BaseModel):
    message: str


class OAuthToken(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[float] = None  # Timestamp for expiration


class EmailIngestion(BaseModel):
    connected_email: EmailStr
    provider: str  # Example: "gmail"
    oauth_token: OAuthToken
