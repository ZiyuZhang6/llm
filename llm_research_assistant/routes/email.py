from fastapi import APIRouter, Depends, HTTPException
from llm_research_assistant.services.mongo_service import (
    get_email_ingestion,
    create_email_ingestion,
    remove_email_ingestion,
)
from llm_research_assistant.services.email_service import EmailService
from llm_research_assistant.dependencies import get_db, get_current_user
from llm_research_assistant.schemas.email import EmailIngestion


router = APIRouter(prefix="/email", tags=["email"])


@router.post("/connect")
async def connect_email(
    email_ingestion: EmailIngestion,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["_id"]

    """Connect a user's email for ingestion"""
    existing = await get_email_ingestion(user_id)

    if existing:
        raise HTTPException(status_code=409, detail="Email is already connected")

    # If no existing email ingestion is found, create a new one
    await create_email_ingestion(user_id, email_ingestion)
    return {"message": "Email connected successfully"}


@router.post("/disconnect")
async def disconnect_email(
    db=Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Disconnect a user's email ingestion"""
    user_id = current_user["_id"]  # Get the user_id from the user document
    existing = await get_email_ingestion(user_id)

    if not existing:
        raise HTTPException(status_code=400, detail="No email ingestion connected")

    await remove_email_ingestion(user_id)
    return {"message": "Email ingestion disconnected successfully"}


@router.get("/fetch")
async def fetch_emails(
    db=Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Fetch academic papers only if email ingestion is connected"""
    user_id = current_user["_id"]

    email_ingestion = await get_email_ingestion(user_id)

    if not email_ingestion:
        raise HTTPException(status_code=400, detail="Email ingestion not connected")

    email_service = EmailService(user_id)
    await email_service.authenticate()
    papers = await email_service.list_papers()
    return papers


@router.get("/connected")
async def get_connected_email(
    current_user: dict = Depends(get_current_user), db=Depends(get_db)
):
    """Return the connected email for the authenticated user"""
    user_id = current_user["_id"]  # Get user_id from the current_user object

    email_ingestion = await get_email_ingestion(user_id)

    if not email_ingestion:
        raise HTTPException(status_code=400, detail="No email ingestion connected")

    return {"connected_email": (email_ingestion["connected_email"])}


@router.get("/fetch_and_process")
async def fetch_and_process_emails(
    db=Depends(get_db), current_user: dict = Depends(get_current_user)
):
    """Fetch academic papers only if email ingestion is connected"""
    user_id = current_user["_id"]

    email_ingestion = await get_email_ingestion(user_id)

    if not email_ingestion:
        raise HTTPException(status_code=400, detail="Email ingestion not connected")

    # email_service = EmailService(user_id)#pass the email not the userid
    email_service = EmailService(user_id, email_ingestion["connected_email"])
    await email_service.authenticate()
    await email_service.process_academic_papers(user_id=user_id, max_results=30)

    return {"message": "Academic papers fetched and processed successfully."}
