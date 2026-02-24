import io

from fastapi import APIRouter, UploadFile

from snakesss.lib.clients.openai import openai_client

router = APIRouter()


@router.post("/audio/transcribe")
def transcribe_audio(
    audio_file: UploadFile,
):
    """Transcribes audio using OpenAI's Whisper API."""

    file = audio_file.file.read()
    buffer = io.BytesIO(file)
    buffer.name = "audio.m4a"

    transcription = openai_client.audio.transcriptions.create(model="whisper-1", file=buffer)

    return {"result": transcription.text}
