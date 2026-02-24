import base64

from fastapi import APIRouter, UploadFile

from snakesss.lib.clients.openai import openai_client

router = APIRouter()


def get_image_description(image_bytes: bytes):
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    completion = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        ],
        max_tokens=1000,
    )

    return completion.choices[0].message.content


@router.post("/image")
async def vision(image: UploadFile):
    response = get_image_description(image.file.read())

    return response


@router.post("/images/embedding")
def image_embedding(image_file: UploadFile):
    """
    Extracts image embeddings using OpenAI's CLIP model
    """
    file = image_file.file.read()

    # Encode the image bytes to base64
    try:
        image_description = get_image_description(file)
        if not image_description:
            raise Exception("Failed to get image description")
    except Exception as e:
        return {"error": str(e)}

    # Call the OpenAI API to get the embedding
    response = openai_client.embeddings.create(model="text-embedding-ada-002", input=image_description)

    return {"embedding": response.data[0].embedding}
