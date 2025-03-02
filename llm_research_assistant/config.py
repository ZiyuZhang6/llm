import os
from pydantic import BaseSettings

from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb+srv://...your-uri-here...")
    MONGODB_URI: str = os.getenv("MONGODB_URI")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME")
    # MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "mydatabase")

    class Config:
        env_file = "../.env"


settings = Settings()
