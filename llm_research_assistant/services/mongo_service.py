from bson import ObjectId
from db import papers_collection


async def store_paper_metadata(filename, pdf_url, user_id):
    """Stores metadata in MongoDB and returns the document ID."""
    paper_doc = {
        "title": filename,
        "owner_id": str(user_id),
        "shared": False,
        "pdf_url": pdf_url,
    }
    result = await papers_collection.insert_one(paper_doc)
    return str(result.inserted_id)  # Return the ObjectId as a string


async def get_paper_metadata(paper_id):
    """Retrieves paper metadata from MongoDB."""
    paper = await papers_collection.find_one({"_id": ObjectId(paper_id)})
    if not paper:
        return None
    return paper


async def delete_paper_metadata(paper_id):
    """Deletes a paper's metadata from MongoDB."""
    result = await papers_collection.delete_one({"_id": ObjectId(paper_id)})
    return result.deleted_count > 0  # Returns True if deletion was successful
