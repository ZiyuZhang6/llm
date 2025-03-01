import os
import jwt
from datetime import datetime, timedelta
from typing import Union

from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("API_SECRET_KEY")
ALGORITHM = "HS256"


def create_access_token(data: dict, expires_delta: Union[int, float] = 30):
    """
    Create a JWT with payload 'data' that expires in 'expires_delta' minutes by default.
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_delta)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode the JWT. Raises jwt.ExpiredSignatureError if token is expired,
    or jwt.InvalidTokenError if token is invalid.
    """
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    return payload
