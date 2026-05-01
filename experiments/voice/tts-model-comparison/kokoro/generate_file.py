import argparse
from pathlib import Path

import soundfile as sf
from kokoro import KPipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Kokoro TTS audio from a text file.")
    parser.add_argument("--text-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--voice", default="af_heart")
    parser.add_argument("--lang-code", default="a")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    text = Path(args.text_file).read_text(encoding="utf-8").strip()
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    pipeline = KPipeline(lang_code=args.lang_code)
    generator = pipeline(text, voice=args.voice)

    chunks = []
    for _, _, audio in generator:
        chunks.append(audio)

    if not chunks:
        raise RuntimeError("Kokoro did not generate audio.")

    if len(chunks) == 1:
        sf.write(output_path, chunks[0], 24000)
        return

    import numpy as np

    sf.write(output_path, np.concatenate(chunks), 24000)


if __name__ == "__main__":
    main()
