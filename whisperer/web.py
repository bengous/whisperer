"""Local Flask UI for Whisperer."""

from __future__ import annotations

import argparse
import logging
import re
import tempfile
from pathlib import Path
from typing import Any

from flask import Flask, render_template, request, send_from_directory

from whisperer.core import (
    DEFAULT_MODEL,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_OUTPUT_FORMAT,
    MODELS,
    OUTPUT_FORMATS,
    TranscriptionOptions,
    WhispererError,
    is_supported,
    run_pipeline,
)

LANGUAGE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{1,15}$")


def _fmt_ts(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    whole_seconds = int(seconds % 60)
    if hours:
        return f"{hours}:{minutes:02d}:{whole_seconds:02d}"
    return f"{minutes}:{whole_seconds:02d}"


def _upload_name(filename: str) -> str:
    return Path(filename.replace("\\", "/")).name


def _valid_language(language: str | None) -> bool:
    return not language or bool(LANGUAGE_RE.fullmatch(language))


def _view_model(result: Any, model_name: str, output_format: str) -> dict[str, Any]:
    transcription = result.transcription
    return {
        "text": transcription.get("text", ""),
        "segments": [
            {
                "start": _fmt_ts(float(segment["start"])),
                "end": _fmt_ts(float(segment["end"])),
                "text": str(segment.get("text", "")).strip(),
            }
            for segment in transcription.get("segments", [])
            if "start" in segment and "end" in segment
        ],
        "language": transcription.get("language", "?"),
        "model": model_name,
        "format": output_format,
        "files": [path.name for path in result.output_files if path.exists()],
    }


def create_app(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Flask:
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        error = None
        result = None

        if request.method == "POST":
            file = request.files.get("file")
            model_name = request.form.get("model", DEFAULT_MODEL)
            language = request.form.get("language", "") or None
            output_format = request.form.get("format", DEFAULT_OUTPUT_FORMAT)

            if not file or not file.filename:
                error = "No file selected."
            elif model_name not in MODELS:
                error = f"Unsupported model: {model_name}"
            elif output_format not in OUTPUT_FORMATS:
                error = f"Unsupported format: {output_format}"
            elif not _valid_language(language):
                error = "Invalid language code."
            else:
                filename = _upload_name(file.filename)
                if not filename or not is_supported(Path(filename)):
                    error = f"Unsupported input file: {filename or file.filename}"
                else:
                    try:
                        with tempfile.TemporaryDirectory(prefix="whisperer_upload_") as tmp:
                            upload_path = Path(tmp) / filename
                            file.save(upload_path)
                            pipeline_result = run_pipeline(
                                TranscriptionOptions(
                                    input_path=upload_path,
                                    output_dir=output_dir,
                                    model=model_name,
                                    language=language,
                                    output_format=output_format,
                                )
                            )
                            result = _view_model(pipeline_result, model_name, output_format)
                    except WhispererError as exc:
                        error = str(exc)
                    except Exception as exc:
                        app.logger.exception("Unexpected web transcription failure")
                        error = f"Unexpected error: {exc}"

        return render_template(
            "index.html",
            models=MODELS,
            formats=OUTPUT_FORMATS,
            default_model=DEFAULT_MODEL,
            default_format="srt",
            error=error,
            result=result,
        )

    @app.route("/outputs/<path:filename>")
    def view_file(filename: str):
        return send_from_directory(output_dir.resolve(), filename)

    @app.route("/download/<path:filename>")
    def download_file(filename: str):
        return send_from_directory(output_dir.resolve(), filename, as_attachment=True)

    return app


app = create_app()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Whisperer local web UI")
    parser.add_argument("--port", "-p", type=int, default=5000, help="port (default: 5000)")
    parser.add_argument("--host", default="127.0.0.1", help="host (default: 127.0.0.1)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="[whisperer] %(message)s")
    print(f"[whisperer] Web UI: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
