import os
from pydantic import BaseSettings

from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    # MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb+srv://...your-uri-here...")
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb+srv://z1095395278:Zzy728371@cluster0.qc8qe.mongodb.net/?")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "Cluster0")
    # MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "mydatabase")

    class Config:
        env_file = "../.env"


settings = Settings()
