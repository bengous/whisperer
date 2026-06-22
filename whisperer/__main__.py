from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from whisperer.core import (
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OUTPUT_FORMAT,
    MODELS,
    OUTPUT_FORMATS,
    TranscriptionOptions,
    WhispererError,
    run_pipeline,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="whisperer",
        description="Transcribe audio/video files locally using Whisper.",
        epilog=(
            "Examples:\n"
            "  whisperer demo.mp4\n"
            "  whisperer audio.wav --model large --language fr\n"
            "  whisperer meeting.mp4 --format srt --output-dir results/\n"
            "  whisperer input.mov --keep-intermediate\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("input", help="audio or video file to transcribe")
    parser.add_argument(
        "--model",
        "-m",
        default=DEFAULT_MODEL,
        choices=MODELS,
        help=f"Whisper model to use (default: {DEFAULT_MODEL})",
    )
    parser.add_argument(
        "--language",
        "-l",
        default=None,
        help="language code, e.g. 'fr', 'en' (default: auto-detect)",
    )
    parser.add_argument(
        "--format",
        "-f",
        default=DEFAULT_OUTPUT_FORMAT,
        choices=OUTPUT_FORMATS,
        help=f"output format (default: {DEFAULT_OUTPUT_FORMAT})",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default=str(DEFAULT_OUTPUT_DIR),
        help=f"output directory (default: {DEFAULT_OUTPUT_DIR}/)",
    )
    parser.add_argument(
        "--keep-intermediate",
        action="store_true",
        help="keep intermediate audio files extracted or converted for Whisper",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="show Whisper's detailed output during transcription",
    )
    return parser.parse_args(argv)


def options_from_args(args: argparse.Namespace) -> TranscriptionOptions:
    return TranscriptionOptions(
        input_path=Path(args.input),
        output_dir=Path(args.output_dir),
        model=args.model,
        language=args.language,
        output_format=args.format,
        keep_intermediate=args.keep_intermediate,
        verbose=args.verbose,
    )


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="[whisperer] %(message)s")
    args = parse_args(argv)
    try:
        run_pipeline(options_from_args(args))
    except WhispererError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
