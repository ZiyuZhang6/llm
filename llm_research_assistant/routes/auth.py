from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from db import users_collection
from security import verify_password
from jwt import create_access_token
from schemas.users import UserCreate

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/login")
async def login(login_req: LoginRequest):
    """
    Verify user credentials, return JWT if valid.
    """
    user = await users_collection.find_one({"email": login_req.email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    if not verify_password(login_req.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Build a JWT with minimal user info: e.g. str(ObjectId)
    user_id = str(user["_id"])
    access_token = create_access_token(data={"sub": user_id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/register")
async def register_user(user_in: UserCreate):
    """
    Create a new user, if your app allows self-registration.
    """
    # Check duplicate
    existing = await users_collection.find_one({"email": user_in.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    from security import hash_password

    hashed = hash_password(user_in.password)
    new_user_doc = {
        "name": user_in.name,
        "email": user_in.email,
        "password_hash": hashed,
    }
    result = await users_collection.insert_one(new_user_doc)
    return {"message": "User created", "user_id": str(result.inserted_id)}
