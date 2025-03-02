"""
Uses the authenticated EmailService object to interact with the Gmail API
,retrieve emails, filter them, and process attachments.
"""
from googleapiclient.discovery import build
import re
import base64
from googleapiclient.errors import HttpError


def get_gmail_service(creds):
    """Create and return Gmail service using authenticated credentials."""
    return build("gmail", "v1", credentials=creds)


def list_messages(
    service, user_id="me", query="in:inbox", max_results=10
):  # limit msg for 10 testing
    """List messages from the Gmail account."""
    messages = []
    response = (
        service.users()
        .messages()
        .list(userId=user_id, q=query, maxResults=max_results)
        .execute()
    )

    while "messages" in response:
        messages.extend(response["messages"])
        if len(messages) >= max_results:
            break  # Exit once we've hit the limit
        if "nextPageToken" in response:
            page_token = response["nextPageToken"]
            response = (
                service.users()
                .messages()
                .list(
                    userId=user_id,
                    q=query,
                    pageToken=page_token,
                    maxResults=max_results,
                )
                .execute()
            )
        else:
            break
    return messages


def filter_academic_emails(messages, service, user_id="me"):
    """
    Filter emails related to academic content
    based on sender, subject, and PDF attachments.
    """
    # Define filtering criteria
    ALLOWED_SENDERS = [
        "arxiv.org",
        "researchgate.net",
        "academia.edu",
        "ieee.org",
        "springer.com",
        "elsevier.com",
        "wiley.com",
        "nature.com",
        "sciencedirect.com",
        "cambridge.org",
        "oxfordjournals.org",
    ]

    UNIVERSITY_DOMAINS = [".edu", ".ac.uk", ".ac.in", ".ac.jp", ".ac.de"]

    KEYWORDS = [
        "research paper",
        "published",
        "preprint",
        "journal",
        "paper",
        "conference",
        "accepted paper",
        "proceedings",
        "arXiv",
        "DOI",
    ]

    filtered_messages = []

    for message in messages:
        msg = service.users().messages().get(userId=user_id, id=message["id"]).execute()

        sender = None
        subject = None
        for header in msg["payload"]["headers"]:
            if header["name"] == "From":
                sender = header["value"]
            elif header["name"] == "Subject":
                subject = header["value"]

        # Extract sender domain
        match = re.search(r"@([\w.-]+)", sender)

        sender_domain = match.group(1) if match else ""

        # Check if sender is academic
        is_academic_sender = any(
            domain in sender_domain for domain in ALLOWED_SENDERS
        ) or any(sender_domain.endswith(edu) for edu in UNIVERSITY_DOMAINS)

        # Check if subject contains research-related keywords
        is_research_related = any(
            keyword.lower() in subject.lower() for keyword in KEYWORDS
        )

        # Check if email has a PDF attachment
        has_pdf = False
        if "parts" in msg["payload"]:
            for part in msg["payload"]["parts"]:
                if part.get("filename") and part.get("mimeType") == "application/pdf":
                    has_pdf = True
                    break

        # If all conditions match, add to filtered messages
        if is_academic_sender and is_research_related and has_pdf:
            filtered_messages.append(msg)

    return filtered_messages


async def get_attachment(service, msg_id):
    """Fetch the attachment from an email by message ID."""
    try:
        message = service.users().messages().get(userId="me", id=msg_id).execute()
        for part in message["payload"]["parts"]:
            # Check if the part is an attachment
            if part["filename"] and part["body"].get("attachmentId"):
                attachment = (
                    service.users()
                    .messages()
                    .attachments()
                    .get(userId="me", messageId=msg_id, id=part["body"]["attachmentId"])
                    .execute()
                )

                data = attachment["data"]
                file_data = base64.urlsafe_b64decode(data.encode("UTF-8"))
                file_name = part["filename"]
                return file_data, file_name  # Return file content and filename

        return None, None
    except HttpError as error:
        raise Exception(f"An error occurred: {error}")
