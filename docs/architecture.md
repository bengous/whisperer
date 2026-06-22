# Architecture

Whisperer has two edges and one pipeline:

- `whisperer.__main__`: CLI parsing, logging setup, exit codes.
- `whisperer.web`: local Flask upload UI, form validation, download routes.
- `whisperer.core`: validation, ffprobe/ffmpeg commands, Whisper call, writers.

The core raises `WhispererError` for user-facing failures. CLI and web convert
that into stderr or an HTML error. Unexpected web failures are logged by Flask
and shown as errors instead of being swallowed.

## Pipeline

1. Validate input path, extension, model, and output format.
2. Check runtime dependencies: `ffmpeg`, `ffprobe`, and `openai-whisper`.
3. If input is video, extract audio to a temporary WAV.
4. If input is audio but not WAV mono 16 kHz, convert it to a temporary WAV.
5. Load the selected Whisper model and transcribe.
6. Write output with `whisper.utils.get_writer`.
7. Optionally copy the intermediate WAV to the output directory.

Temporary files live in `tempfile.TemporaryDirectory` and are removed unless
`--keep-intermediate` is used.

## Boundaries

- Source: `whisperer/`, `tests/`, `scripts/`, `docs/`, `README.md`,
  `pyproject.toml`, `AGENTS.md`.
- Generated/local: `outputs/`, root media files, root transcript exports,
  caches, `.venv/`, `.agents/`, local `plans/`, `skills-lock.json`.
- External runtime tools: ffmpeg/ffprobe, Whisper models, GPU/CPU state.

Tests should use dependency injection in `run_pipeline` rather than invoking
real ffmpeg, Whisper, model downloads, or GPU work.
