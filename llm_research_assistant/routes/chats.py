from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from llm_research_assistant.db import chats_collection
from llm_research_assistant.schemas.chats import ChatCreate, ChatUpdate, ChatResponse
from langchain_core.messages import HumanMessage, AIMessage
from llm_research_assistant.rag.chain import (
    get_documents_from_web,
    create_db,
    create_chain,
    process_chat,
)

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
            id=str(c["_id"]),
            owner_id=c["owner_id"],
            message_chain=c["message_chain"],
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
    return None


# ------------------------
# Chat Processing Endpoints
# ------------------------

# Initialize the chain (this example uses a fixed URL; adjust as needed)
docs = get_documents_from_web("https://python.langchain.com/docs/expression_language/")
vector_store = create_db(docs)
chain = create_chain(vector_store)


# Pydantic models for chat processing
class ChatMessage(BaseModel):
    role: str  # "human" or "ai"
    content: str


class ChatRequest(BaseModel):
    question: str
    chat_history: Optional[List[ChatMessage]] = []


class ChatProcessResponse(BaseModel):
    answer: str


@router.post("/chat", response_model=ChatProcessResponse)
def chat_endpoint(request: ChatRequest):
    # Convert incoming chat history to LangChain message objects
    history = []
    for msg in request.chat_history:
        if msg.role.lower() == "human":
            history.append(HumanMessage(content=msg.content))
        elif msg.role.lower() == "ai":
            history.append(AIMessage(content=msg.content))
    try:
        answer = process_chat(chain, request.question, history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ChatProcessResponse(answer=answer)


@router.post("/chat/{chat_id}", response_model=ChatProcessResponse)
async def continue_chat(chat_id: str, request: ChatRequest):
    # Retrieve the stored chat from the DB
    chat_record = await chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat_record:
        raise HTTPException(status_code=404, detail="Chat not found")
    stored_history = chat_record.get("message_chain", [])
    history = []
    for msg in stored_history:
        role = msg.get("role", "").lower()
        content = msg.get("content", "")
        if role == "human":
            history.append(HumanMessage(content=content))
        elif role == "ai":
            history.append(AIMessage(content=content))
    try:
        answer = process_chat(chain, request.question, history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    new_human_msg = {"role": "human", "content": request.question}
    new_ai_msg = {"role": "ai", "content": answer}
    updated_history = stored_history + [new_human_msg, new_ai_msg]
    await chats_collection.update_one(
        {"_id": ObjectId(chat_id)},
        {"$set": {"message_chain": updated_history}},
    )
    return ChatProcessResponse(answer=answer)
