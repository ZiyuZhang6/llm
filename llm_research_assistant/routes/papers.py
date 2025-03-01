from fastapi import APIRouter, HTTPException, status, Query, UploadFile, Depends, File
from typing import List, Optional
from bson import ObjectId
import fitz
from llm_research_assistant.services.s3_service import (
    upload_pdf_to_s3,
    get_pdf_url_from_s3,
    delete_pdf_from_s3,
)
from llm_research_assistant.services.mongo_service import (
    store_paper_metadata,
    get_paper_metadata,
    delete_paper_metadata,
)

from llm_research_assistant.db import papers_collection
from llm_research_assistant.dependencies import get_current_user
from llm_research_assistant.schemas.papers import (
    PaperUpdate,
    PaperResponse,
)

router = APIRouter(prefix="/papers", tags=["papers"])


@router.post("/", response_model=PaperResponse, status_code=status.HTTP_201_CREATED)
async def create_paper(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """Uploads a PDF to S3 and stores metadata in MongoDB."""

    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Validate PDF structure
    await validate_pdf(file)

    # Upload file to S3
    pdf_url = await upload_pdf_to_s3(file, current_user["_id"])

    # Store metadata in MongoDB
    paper_id = await store_paper_metadata(file.filename, pdf_url, current_user["_id"])

    return PaperResponse(
        id=paper_id,
        title=file.filename,
        pdf_url=pdf_url,
        shared=False,
        owner_id=str(current_user["_id"]),
    )


@router.get("/", response_model=List[PaperResponse])
async def list_papers(
    skip: int = 0, limit: int = Query(10, le=100), owner_id: Optional[str] = None
):
    """
    List papers, optionally filtered by owner_id.
    Paginated by skip/limit.
    """
    query = {}
    if owner_id:
        # We assume owner_id is a string (the str(ObjectId))
        query["owner_id"] = owner_id

    cursor = papers_collection.find(query).skip(skip).limit(limit)
    papers = await cursor.to_list(length=limit)

    return [
        PaperResponse(
            id=str(p["_id"]),
            title=p["title"],
            pdf_url=p["pdf_url"],
            shared=p.get("shared", False),
            owner_id=p["owner_id"],
        )
        for p in papers
    ]


@router.get("/{paper_id}", response_model=PaperResponse)
async def get_paper_by_id(paper_id: str):
    """Retrieve a single paper by its ObjectId."""

    paper = await get_paper_metadata(paper_id)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    return PaperResponse(
        id=str(paper["_id"]),
        title=paper["title"],
        pdf_url=paper["pdf_url"],
        shared=paper.get("shared", False),
        owner_id=paper["owner_id"],
    )


@router.put("/{paper_id}", response_model=PaperResponse)
async def update_paper(paper_id: str, paper_in: PaperUpdate):
    """Update paper metadata (title or shared status)."""

    paper = await get_paper_metadata(paper_id)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    update_doc = {}
    if paper_in.title is not None:
        update_doc["title"] = paper_in.title
    if paper_in.shared is not None:
        update_doc["shared"] = paper_in.shared

    if update_doc:
        await papers_collection.update_one(
            {"_id": ObjectId(paper_id)}, {"$set": update_doc}
        )

    updated_paper = await get_paper_metadata(paper_id)
    return PaperResponse(
        id=str(updated_paper["_id"]),
        title=updated_paper["title"],
        pdf_url=updated_paper["pdf_url"],
        shared=updated_paper.get("shared", False),
        owner_id=updated_paper["owner_id"],
    )


@router.delete("/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_paper(paper_id: str):
    """
    Delete paper form s3 and mongodb by paper ID.
    """
    # Get paper metadata to retrieve the S3 file URL
    paper = await get_paper_metadata(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    try:
        # Delete file from S3
        await delete_pdf_from_s3(paper["pdf_url"])

        # Delete metadata from MongoDB
        deleted = await delete_paper_metadata(paper_id)

        if not deleted:
            raise HTTPException(
                status_code=500, detail="Failed to delete paper metadata from MongoDB."
            )

        return None  # 204 No Content
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download/{paper_id}")
async def download_pdf(paper_id: str, current_user: dict = Depends(get_current_user)):
    """Retrieve the S3 URL for a PDF download.
    If the paper is not shared, only the owner can download it."""

    paper = await get_paper_metadata(paper_id)

    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found.")

    # If the paper is shared=False, then ensure the current user is the owner.
    if not paper.get("shared", False) and str(current_user["_id"]) != paper["owner_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to download this file.",
        )

    return await get_pdf_url_from_s3(paper_id, paper["pdf_url"])


async def validate_pdf(file: UploadFile):
    """Validate that the uploaded file is a proper PDF."""
    try:
        pdf_data = await file.read()
        doc = fitz.open(stream=pdf_data, filetype="pdf")  # Validate PDF
        if doc.page_count < 1:  # zero pages
            raise HTTPException(status_code=400, detail="Invalid PDF file.")
        return pdf_data
    except Exception:
        raise HTTPException(status_code=400, detail="Corrupt or unreadable PDF.")
