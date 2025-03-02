from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from langchain_core.messages import HumanMessage, AIMessage
from llm_research_assistant.rag.chain import (
    get_documents_from_web,
    create_db,
    create_chain,
    process_chat,
)
from llm_research_assistant.db import chats_collection
from bson import ObjectId

router = APIRouter(prefix="/rag", tags=["rag"])

docs = get_documents_from_web("https://python.langchain.com/docs/expression_language/")
vector_store = create_db(docs)
chain = create_chain(vector_store)


class ChatMessage(BaseModel):
    role: str  # "human" or "ai"
    content: str


class ChatRequest(BaseModel):
    question: str
    chat_history: Optional[List[ChatMessage]] = []


class ChatResponse(BaseModel):
    answer: str


@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(request: ChatRequest):
    """
    API endpoint for chatting with the RAG assistant.
    Accepts a question and optional chat history; returns the generated answer.
    """
    # Convert the incoming chat history (as a list of ChatMessage)
    # into the chain's expected message objects.
    history = []
    for msg in request.chat_history:
        if msg.role.lower() == "human":
            history.append(HumanMessage(content=msg.content))
        elif msg.role.lower() == "ai":
            history.append(AIMessage(content=msg.content))
        else:
            # Optionally ignore or handle unexpected roles.
            continue

    try:
        answer = process_chat(chain, request.question, history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ChatResponse(answer=answer)


@router.post("/chat/{chat_id}", response_model=ChatResponse)
async def continue_chat(chat_id: str, request: ChatRequest):
    """
    Endpoint to continue an existing chat conversation.

    The chat history is retrieved from the database (using the provided chat_id).
    Then the new question is processed along with that history.
    Finally, the updated conversation (with the new question and answer)
    is saved back to the database.
    """
    # Retrieve the stored chat from the database
    chat_record = await chats_collection.find_one({"_id": ObjectId(chat_id)})
    if not chat_record:
        raise HTTPException(status_code=404, detail="Chat not found")

    # Extract the stored chat history (assumed to be a list of dicts
    #  with keys "role" and "content")
    stored_history = chat_record.get("message_chain", [])

    # Convert stored history into LangChain message objects
    history = []
    for msg in stored_history:
        role = msg.get("role", "").lower()
        content = msg.get("content", "")
        if role == "human":
            history.append(HumanMessage(content=content))
        elif role == "ai":
            history.append(AIMessage(content=content))

    # Process the new question with the existing chat history
    try:
        answer = process_chat(chain, request.question, history)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Prepare new messages to append
    new_human_msg = {"role": "human", "content": request.question}
    new_ai_msg = {"role": "ai", "content": answer}

    # Update the stored chat history by appending new messages
    updated_history = stored_history + [new_human_msg, new_ai_msg]
    chats_collection.update_one(
        {"_id": ObjectId(chat_id)}, {"$set": {"message_chain": updated_history}}
    )

    return ChatResponse(answer=answer)
