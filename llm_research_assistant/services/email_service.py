# handle interactions with the Gmail API (or future email providers).
"""Store & Refresh OAuth Tokens)"""
import time
import os
from dotenv import load_dotenv
from fastapi import HTTPException
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from llm_research_assistant.services.mongo_service import (
    get_email_ingestion,
    update_email_ingestion,
    store_paper_metadata,
)
from llm_research_assistant.services.s3_service import upload_pdf_to_s3
from llm_research_assistant.services.gmail_service import (
    list_messages,
    filter_academic_emails,
    get_attachment,
)
from llm_research_assistant.routes.papers import calculate_file_hash

# Load environment variables
load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class EmailService:
    def __init__(self, user_id, user_email):
        self.user_id = user_id
        self.user_email = user_email
        self.creds = None
        self.service = None

    async def authenticate(self):
        """Authenticate and refresh token if expired."""
        try:
            # email_ingestion = await get_email_ingestion(self.user_email)
            email_ingestion = await get_email_ingestion(self.user_id)

            if email_ingestion:
                oauth_token = email_ingestion.get("oauth_token")

                if oauth_token and oauth_token["expires_at"] < time.time():
                    # Refresh token instead of forcing re-authentication
                    creds = Credentials(
                        token=None,
                        refresh_token=oauth_token["refresh_token"],
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=os.getenv("GOOGLE_CLIENT_ID"),
                        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
                    )
                    creds.refresh(Request())

                    # Store updated token in MongoDB
                    await update_email_ingestion(
                        self.user_id,
                        {
                            "connected_email": self.user_email,
                            "provider": "gmail",
                            "oauth_token": {
                                "access_token": creds.token,
                                "refresh_token": creds.refresh_token,
                                "expires_at": creds.expiry.timestamp(),
                            },
                        },
                    )
                    self.creds = creds
                else:
                    # Perform fresh authentication # idont think i have the json file!!!
                    flow = InstalledAppFlow.from_client_secrets_file(
                        os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json"), SCOPES
                    )
                    self.creds = flow.run_local_server(
                        port=8080, access_type="offline", prompt="consent"
                    )

                # Create Gmail service
                self.service = build("gmail", "v1", credentials=self.creds)

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Gmail Authentication failed: {str(e)}"
            )

    async def get_message_subject(self, message):
        """Extract the subject header from a message."""
        subject = None
        for header in message["payload"]["headers"]:
            if header["name"] == "Subject":
                subject = header["value"]
                break
        return subject

    async def list_papers(self, max_results=30):
        """Fetch the last 'max_results' academic emails."""
        try:
            # List the last 'max_results' messages from the user's inbox
            messages = list_messages(
                self.service, user_id="me", max_results=max_results
            )

            # Filter the messages to find academic emails
            academic_emails = filter_academic_emails(
                messages, self.service, user_id="me"
            )
            return academic_emails

        except Exception as e:
            raise HTTPException(
                status_code=500, detail=f"Error fetching papers: {str(e)}"
            )

    async def process_academic_papers(
        self,
        user_id: str,
        max_results=30,
    ):
        """Process academic papers: fetch, upload to S3, and store in MongoDB."""
        try:
            academic_emails = await self.list_papers(max_results=max_results)

            for email in academic_emails:
                message_id = email["id"]  # Assuming academic emails have 'id' field

                file_data, filename = await get_attachment(self.service, message_id)
                file_hash = calculate_file_hash(file_data)

                if file_data and filename:
                    # Step 1: Upload to S3
                    s3_url = await upload_pdf_to_s3(
                        file_data, user_id, filename, file_hash
                    )  # Upload the file and get the S3 URL
                    print(f"File uploaded to S3: {s3_url}")

                    # Step 2: Store metadata in MongoDB
                    paper_id = await store_paper_metadata(
                        filename, s3_url, user_id, file_hash
                    )  # Store the metadata
                    print(
                        "Metadata stored in MongoDB for {}, Paper ID: {}".format(
                            filename, paper_id
                        )
                    )
                else:
                    print(f"No attachment found for email: {message_id}")
        except Exception as e:
            print(f"Error processing academic papers: {str(e)}")
