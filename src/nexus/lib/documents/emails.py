import os
from email import message_from_bytes
from email.message import Message

from fastapi import File, UploadFile
from nexus.lib.clients.openai import get_openai_chat_completion
from nexus.lib.clients.s3 import s3_client


def get_email_body(msg: Message):
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            disposition = str(part.get("Content-Disposition"))

            # skip any text/plain (txt) attachments
            if ctype == "text/plain" and "attachment" not in disposition:
                return part.get_payload(decode=True)
    # not multipart - i.e. plain text, no attachments
    else:
        return msg.get_payload(decode=True)


async def save_email_attachments(msg: Message):
    for part in msg.walk():
        if part.get_content_maintype() == "multipart":
            continue

        if part.get("Content-Disposition") is None:
            continue

        filename = part.get_filename() or f"attachment-{part.get('Content-ID')}"

        s3_client.put_object(
            Bucket=os.getenv("S3_BUCKET_NAME"),
            Key=f"attachments/{filename}",
            Body=part.get_payload(decode=True),
        )


async def process_email(email: UploadFile = File(...)):
    # Read the email content
    email_content = await email.read()

    # Parse the email
    msg = message_from_bytes(email_content)

    # Retrieve the email body
    body = get_email_body(msg)

    # Process attachments
    await save_email_attachments(msg)

    llm_response = await get_openai_chat_completion(
        system_message="You are a helpful assistant that processes email content.",
        user_message=f"Process this email body: {body}",
    )

    return {
        "message": "Email processed successfully",
        "attachments_saved": "Attachments saved to S3",
        "content": llm_response,
    }
