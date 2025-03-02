from bson import ObjectId
from llm_research_assistant.db import papers_collection, email_ingestion_collection
from llm_research_assistant.schemas.email import EmailIngestion


async def store_paper_metadata(filename, pdf_url, user_id, file_hash):
    """Stores metadata in MongoDB and returns the document ID."""

    # Check if the file with the same hash already exists for the user
    existing_file = await papers_collection.find_one(
        {
            "file_hash": file_hash,
            "owner_id": str(user_id),  # Ensure it is for the current user
        }
    )

    if existing_file:
        # If the file already exists, return the existing document's ID
        print(f"File '{filename}' already exists for user {user_id}")
        return str(existing_file["_id"])  # Return the existing paper ID

    paper_doc = {
        "title": filename,
        "owner_id": str(user_id),
        "shared": False,
        "pdf_url": pdf_url,
        "file_hash": file_hash,  # Store the file hash to prevent duplicate uploads
    }
    result = await papers_collection.insert_one(paper_doc)
    return str(result.inserted_id)  # Return the ObjectId as a string


async def get_paper_metadata(paper_id):
    """Retrieves paper metadata from MongoDB."""
    paper = await papers_collection.find_one({"_id": ObjectId(paper_id)})
    if not paper:
        return None
    return paper


async def delete_paper_metadata(paper_id, user_id):
    """Deletes a paper's metadata from MongoDB."""
    result = await papers_collection.delete_one(
        {"_id": ObjectId(paper_id), "owner_id": str(user_id)}
    )
    return result.deleted_count > 0  # Returns True if deletion was successful


async def create_email_ingestion(user_id: str, email_ingestion_data: EmailIngestion):
    """Store email ingestion credentials asynchronously"""
    print("the email ingestion data inside th create method: ", email_ingestion_data)
    await email_ingestion_collection.insert_one(
        {
            "user_id": user_id,
            "connected_email": email_ingestion_data.connected_email,
            "provider": email_ingestion_data.provider,
            "oauth_token": email_ingestion_data.oauth_token.dict(),
        }
    )


async def get_email_ingestion(user_id: str):
    """Retrieve a user's connected email ingestion details asynchronously"""
    email_ingestion = await email_ingestion_collection.find_one(
        {"user_id": ObjectId(user_id)}
    )
    if not email_ingestion:
        print("No email ingestion found.")  # Add this line for debugging
        return None

    return email_ingestion


async def update_email_ingestion(user_id: str, email_ingestion_data: EmailIngestion):
    """Update email ingestion details for a user"""
    await email_ingestion_collection.update_one(
        {"user_id": ObjectId(user_id)},
        {
            "$set": {
                "connected_email": email_ingestion_data["connected_email"],
                "provider": email_ingestion_data["provider"],
                "oauth_token": email_ingestion_data["oauth_token"],
            }
        },
        upsert=True,
    )


async def remove_email_ingestion(user_id: str):
    """Remove email ingestion details for a user"""
    await email_ingestion_collection.delete_one({"user_id": user_id})
