import boto3
import os
from dotenv import load_dotenv
import asyncio
from io import BytesIO
from llm_research_assistant.db import papers_collection


# Load AWS credentials
load_dotenv()

# Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)

S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")


async def upload_pdf_to_s3(file, user_id, filename, file_hash):
    """Uploads a PDF to S3 and returns the file URL."""

    # Check if the file hash already exists in MongoDB
    existing_file = await papers_collection.find_one({"file_hash": file_hash})

    if existing_file:
        return existing_file["pdf_url"]  # Return the existing URL for this file

    # If the file does not exist, upload it to S3
    s3_file_key = (
        f"papers/{file_hash}/{filename}"  # Use the file hash as part of the key
    )
    try:
        if isinstance(file, bytes):
            file_data = BytesIO(file)  # Convert bytes into a file-like object
        else:
            file_data = file.file  # This works for local file uploads (UploadFile)

        # file.file.seek(0) #for upload
        file_data.seek(0)

        await asyncio.to_thread(
            s3_client.upload_fileobj, file_data, S3_BUCKET_NAME, s3_file_key
        )
        pdf_url = "https://{}.s3.amazonaws.com/{}".format(S3_BUCKET_NAME, s3_file_key)
        return pdf_url
    except Exception as e:
        raise Exception(f"S3 upload failed: {str(e)}")


async def get_pdf_url_from_s3(paper_id, pdf_url, expires_in=3600):
    """
    Returns a presigned S3 URL for the PDF.

    Even though you store a preassigned URL (pdf_url), this function
    extracts the S3 key from that URL and generates a presigned URL
    with a limited lifetime.
    """
    try:
        # Extract the file key from the preassigned URL.
        # Assumes the URL is in the form:
        # https://<bucket-name>.s3.amazonaws.com/<s3_file_key>
        prefix = "https://{}.s3.amazonaws.com/".format(S3_BUCKET_NAME)
        file_key = pdf_url.split(prefix)[-1]

        # Generate a presigned URL for the S3 object.
        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": S3_BUCKET_NAME, "Key": file_key},
            ExpiresIn=expires_in,
        )
        return {"pdf_url": presigned_url}
    except Exception as e:
        raise Exception(f"Failed to generate presigned URL: {str(e)}")


async def delete_pdf_from_s3(pdf_url):
    """Deletes a PDF from S3 using its URL."""
    try:
        # Extract file key from S3 URL
        file_key = pdf_url.split("https://{}.s3.amazonaws.com/".format(S3_BUCKET_NAME))[
            -1
        ]

        # Delete file from S3
        s3_client.delete_object(Bucket=S3_BUCKET_NAME, Key=file_key)
        return True
    except Exception as e:
        raise Exception(f"Failed to delete PDF from S3: {str(e)}")
