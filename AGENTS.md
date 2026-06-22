## Source Of Truth

- Read `README.md`, `docs/architecture.md`, `pyproject.toml`, and current code
  before changing behavior.
- Source files live in `whisperer/`, `tests/`, `scripts/`, `docs/`,
  `.github/`, plus root project metadata.
- Generated/local artifacts are not source: `outputs/`, root media files,
  root transcript exports, `.venv/`, caches, `.agents/`, and local `plans/`.
- Do not edit generated transcripts as if they were source.

## Workflow

- Keep changes minimal and behavior-preserving unless explicitly asked.
- Do not commit, push, publish, create a remote repository, or delete local
  media without explicit human approval.
- Before edits, check whether the behavior belongs in the CLI edge, web edge,
  or `whisperer.core`.
- Core code should raise `WhispererError` with context. CLI/web convert errors
  into user-visible messages.
- Prefer stdlib. Add a dependency only when it is required by runtime behavior.

## Validation

Run:

```bash
bash scripts/check.sh
```

The check must stay fast and must not download Whisper models, require ffmpeg
execution, or require a GPU.

Use fakes/mocks through `run_pipeline` parameters for tests. Do not test quick
paths by invoking real Whisper or heavy media files.

Manual smoke tests on real media are optional and must use tiny non-sensitive
files.

## Local Data

- Keep demos and generated outputs under ignored paths.
- Do not remove or quarantine local media unless the user approves the exact
  list.
- Do not add media fixtures unless they are tiny, non-sensitive, and clearly
  needed. Text fixtures are preferred.

## Acceptance Bar

- `python -m whisperer --help` works.
- `python -m whisperer.web --help` works when dependencies are installed.
- `bash scripts/check.sh` passes or the failure is reported with cause and next
  action.
- Existing behaviors remain: video extraction, audio conversion to WAV mono
  16 kHz, Whisper formats `txt/srt/json/vtt/tsv/all`, model/language options,
  local web UI.
