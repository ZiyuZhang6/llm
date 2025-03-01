import bson
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List
from bson import ObjectId
from llm_research_assistant.db import users_collection
from llm_research_assistant.schemas.users import UserCreate, UserUpdate, UserResponse
from llm_research_assistant.security import hash_password
from llm_research_assistant.dependencies import get_current_user


router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_in: UserCreate):
    # Check for duplicate email
    existing_user = await users_collection.find_one({"email": user_in.email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists.",
        )

    # Hash the password
    hashed = hash_password(user_in.password)

    # Prepare document
    user_doc = {"name": user_in.name, "email": user_in.email, "password_hash": hashed}
    result = await users_collection.insert_one(user_doc)

    # Return the newly created user (without sensitive fields)
    return UserResponse(
        id=str(result.inserted_id), name=user_in.name, email=user_in.email
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """
    Return information about the currently authenticated user.
    """
    return UserResponse(
        id=str(current_user["_id"]),
        name=current_user["name"],
        email=current_user["email"],
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: str):
    """
    Get a user by their ObjectId (string). For admin usage or open usage.
    """
    try:
        obj_id = ObjectId(user_id)
    except bson.errors.InvalidId:
        raise HTTPException(status_code=400, detail=f"Invalid user_id: {user_id}")
    user = await users_collection.find_one({"_id": obj_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(id=str(user["_id"]), name=user["name"], email=user["email"])


@router.get("/", response_model=List[UserResponse])
async def list_users(skip: int = 0, limit: int = Query(10, le=100)):
    cursor = users_collection.find().skip(skip).limit(limit)
    users = await cursor.to_list(length=limit)
    return [
        UserResponse(id=str(u["_id"]), name=u["name"], email=u["email"]) for u in users
    ]


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: str, user_in: UserUpdate):
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    update_doc = {}
    if user_in.name is not None:
        update_doc["name"] = user_in.name
    if user_in.email is not None:
        # Optionally check for duplicates
        existing_email_user = await users_collection.find_one({"email": user_in.email})
        if existing_email_user and existing_email_user["_id"] != user["_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already in use.",
            )
        update_doc["email"] = user_in.email
    if user_in.password is not None:
        update_doc["password_hash"] = hash_password(user_in.password)

    if update_doc:
        await users_collection.update_one(
            {"_id": ObjectId(user_id)}, {"$set": update_doc}
        )

    updated_user = await users_collection.find_one({"_id": ObjectId(user_id)})
    return UserResponse(
        id=str(updated_user["_id"]),
        name=updated_user["name"],
        email=updated_user["email"],
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str):
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    return None  # 204 No Content
