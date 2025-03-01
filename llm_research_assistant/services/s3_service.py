import boto3
import os
from dotenv import load_dotenv

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


async def upload_pdf_to_s3(file, user_id):
    """Uploads a PDF to S3 and returns the file URL."""
    s3_file_key = "papers/{}/{}".format(user_id, file.filename)

    try:
        file.file.seek(0)  # Ensure the file is read from the start
        s3_client.upload_fileobj(file.file, S3_BUCKET_NAME, s3_file_key)
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
