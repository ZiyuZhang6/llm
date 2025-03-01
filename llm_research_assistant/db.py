from motor.motor_asyncio import AsyncIOMotorClient
from llm_research_assistant.config import settings
import asyncio

client = AsyncIOMotorClient(settings.MONGODB_URI)
db = client[settings.MONGODB_DB_NAME]

users_collection = db["users"]
papers_collection = db["papers"]
chats_collection = db["chats"]


async def test_mongodb():
    """Test MongoDB connection asynchronously."""
    try:
        databases = await client.list_database_names()
        print("Connected to MongoDB Atlas! Databases:", databases)
    except Exception as e:
        print("Connection Error:", e)


async def startup():
    await test_mongodb()


# Call the function when running FastAPI
if __name__ == "__main__":
    asyncio.run(startup())  # ✅ Only used if running this file directly
