from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional
from bson import ObjectId

from llm_research_assistant.db import chats_collection
from llm_research_assistant.schemas.chats import ChatCreate, ChatUpdate, ChatResponse

router = APIRouter(prefix="/chats", tags=["chats"])


@router.post("/", response_model=ChatResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(chat_in: ChatCreate):
    doc = {
        "owner_id": chat_in.owner_id,
        "message_chain": chat_in.message_chain,
    }
    result = await chats_collection.insert_one(doc)
    chat = await chats_collection.find_one({"_id": result.inserted_id})

    return ChatResponse(
        id=str(chat["_id"]),
        owner_id=chat["owner_id"],
        message_chain=chat["message_chain"],
    )


@router.get("/", response_model=List[ChatResponse])
async def list_chats(
    skip: int = 0, limit: int = Query(10, le=100), owner_id: Optional[str] = None
):
    query = {}
    if owner_id:
        query["owner_id"] = owner_id

    cursor = chats_collection.find(query).skip(skip).limit(limit)
    chats = await cursor.to_list(length=limit)

    return [
        ChatResponse(
            id=str(c["_id"]), owner_id=c["owner_id"], message_chain=c["message_chain"]
        )
        for c in chats
    ]


@router.get("/{chat_id}", response_model=ChatResponse)
async def get_chat_by_id(chat_id: str):
    chat = await chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    return ChatResponse(
        id=str(chat["_id"]),
        owner_id=chat["owner_id"],
        message_chain=chat["message_chain"],
    )


@router.put("/{chat_id}", response_model=ChatResponse)
async def update_chat(chat_id: str, chat_in: ChatUpdate):
    chat = await chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat:
        raise HTTPException(status_code=404, detail="Chat not found")

    update_doc = {}
    if chat_in.message_chain is not None:
        update_doc["message_chain"] = chat_in.message_chain

    if update_doc:
        await chats_collection.update_one(
            {"_id": ObjectId(chat_id)}, {"$set": update_doc}
        )

    updated_chat = await chats_collection.find_one({"_id": ObjectId(chat_id)})
    return ChatResponse(
        id=str(updated_chat["_id"]),
        owner_id=updated_chat["owner_id"],
        message_chain=updated_chat["message_chain"],
    )


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chat(chat_id: str):
    result = await chats_collection.delete_one({"_id": ObjectId(chat_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Chat not found")

    return None  # 204
