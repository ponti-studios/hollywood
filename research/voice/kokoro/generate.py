from pathlib import Path

import soundfile as sf
from kokoro import KPipeline

TEXT = (
    "This is Kokoro, an eighty two million parameter open weight text to speech "
    "model running inside a local Docker experiment."
)

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

pipeline = KPipeline(lang_code="a")
generator = pipeline(TEXT, voice="af_heart")

for index, (_, _, audio) in enumerate(generator):
    output_path = OUTPUT_DIR / f"kokoro-{index}.wav"
    sf.write(output_path, audio, 24000)
    print(f"Saved {output_path}")

first_output = OUTPUT_DIR / "kokoro-0.wav"
stable_output = OUTPUT_DIR / "kokoro.wav"
if first_output.exists():
    stable_output.write_bytes(first_output.read_bytes())
    print(f"Saved {stable_output}")
