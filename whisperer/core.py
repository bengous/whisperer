from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("whisperer")

VIDEO_EXTENSIONS = frozenset({".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv", ".wmv", ".m4v"})
AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus"})
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | AUDIO_EXTENSIONS

WRITER_FORMATS = ("txt", "srt", "json", "vtt", "tsv")
OUTPUT_FORMATS = (*WRITER_FORMATS, "all")
MODELS = ("tiny", "base", "small", "medium", "large", "large-v2", "large-v3", "turbo")

DEFAULT_MODEL = "turbo"
DEFAULT_OUTPUT_FORMAT = "txt"
DEFAULT_OUTPUT_DIR = Path("outputs")

Runner = Callable[..., subprocess.CompletedProcess[str]]
Transcriber = Callable[[Path, str, str | None, bool], Mapping[str, Any]]
Writer = Callable[[Mapping[str, Any], Path, Path, str], tuple[Path, ...]]


class WhispererError(RuntimeError):
    """User-facing failure with enough context for CLI and web edges."""


@dataclass(frozen=True)
class AudioInfo:
    codec_name: str | None
    sample_rate: str | None
    channels: int | None

    @property
    def is_whisper_ready(self) -> bool:
        return self.codec_name == "pcm_s16le" and self.sample_rate == "16000" and self.channels == 1


@dataclass(frozen=True)
class TranscriptionOptions:
    input_path: Path
    output_dir: Path = DEFAULT_OUTPUT_DIR
    model: str = DEFAULT_MODEL
    language: str | None = None
    output_format: str = DEFAULT_OUTPUT_FORMAT
    keep_intermediate: bool = False
    verbose: bool = False


@dataclass(frozen=True)
class PipelineResult:
    output_dir: Path
    output_files: tuple[Path, ...]
    kept_intermediate: Path | None
    detected_language: str | None
    transcription: Mapping[str, Any]


def log(message: str) -> None:
    LOGGER.info(message)


def check_dependencies() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if not shutil.which(name)]
    if missing:
        raise WhispererError(
            f"Missing system dependency: {', '.join(missing)}. Install ffmpeg and retry."
        )

    try:
        import whisper  # noqa: F401
    except ImportError as exc:
        raise WhispererError(
            "Missing Python dependency: openai-whisper. Install the package with `pip install -e .`."
        ) from exc


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTENSIONS


def is_supported(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


def build_ffprobe_command(path: Path) -> list[str]:
    return [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=codec_name,sample_rate,channels",
        "-of",
        "json",
        str(path),
    ]


def build_ffmpeg_command(input_path: Path, output_path: Path) -> list[str]:
    return [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "16000",
        "-ac",
        "1",
        str(output_path),
    ]


def _run_command(cmd: list[str], runner: Runner, failure_message: str) -> subprocess.CompletedProcess[str]:
    try:
        return runner(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError as exc:
        raise WhispererError(f"{cmd[0]} not found in PATH.") from exc
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        suffix = f":\n{detail}" if detail else "."
        raise WhispererError(f"{failure_message}{suffix}") from exc


def _int_or_none(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def probe_audio(path: Path, runner: Runner = subprocess.run) -> AudioInfo:
    result = _run_command(build_ffprobe_command(path), runner, f"ffprobe failed for {path}")
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise WhispererError(f"ffprobe returned invalid JSON for {path}.") from exc

    streams = data.get("streams", []) if isinstance(data, dict) else []
    if not streams:
        raise WhispererError(f"No audio stream found in {path}.")

    first = streams[0]
    if not isinstance(first, dict):
        raise WhispererError(f"ffprobe returned an invalid audio stream for {path}.")

    return AudioInfo(
        codec_name=first.get("codec_name"),
        sample_rate=str(first.get("sample_rate")) if first.get("sample_rate") is not None else None,
        channels=_int_or_none(first.get("channels")),
    )


def needs_conversion(path: Path, runner: Runner = subprocess.run) -> bool:
    if path.suffix.lower() != ".wav":
        return True
    return not probe_audio(path, runner).is_whisper_ready


def ffmpeg_convert(input_path: Path, output_path: Path, runner: Runner = subprocess.run) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _run_command(
        build_ffmpeg_command(input_path, output_path),
        runner,
        f"ffmpeg failed while preparing {input_path}",
    )


def prepare_audio(input_path: Path, tmp_dir: Path, runner: Runner = subprocess.run) -> Path:
    if is_video(input_path):
        log(f"Extracting audio from video: {input_path.name}")
        output_path = tmp_dir / f"{input_path.stem}.wav"
        ffmpeg_convert(input_path, output_path, runner)
        return output_path

    if needs_conversion(input_path, runner):
        log(f"Converting audio to WAV mono 16kHz: {input_path.name}")
        output_path = tmp_dir / f"{input_path.stem}.wav"
        ffmpeg_convert(input_path, output_path, runner)
        return output_path

    log(f"Audio already in correct format: {input_path.name}")
    return input_path


def _empty_cuda_cache(torch_module: Any) -> None:
    cuda = getattr(torch_module, "cuda", None)
    if cuda is not None and hasattr(cuda, "empty_cache"):
        cuda.empty_cache()


def transcribe_audio(
    audio_path: Path,
    model_name: str,
    language: str | None,
    verbose: bool,
) -> Mapping[str, Any]:
    try:
        import torch
        import whisper
    except ImportError as exc:
        raise WhispererError(
            "Missing Python dependency for transcription. Install with `pip install -e .`."
        ) from exc

    log(f"Loading model: {model_name}")
    try:
        model = whisper.load_model(model_name)
    except torch.cuda.OutOfMemoryError as exc:
        _empty_cuda_cache(torch)
        raise WhispererError(
            f"CUDA out of memory loading model '{model_name}'. Try a smaller model."
        ) from exc
    except Exception as exc:
        raise WhispererError(f"Could not load Whisper model '{model_name}': {exc}") from exc

    log("Transcribing...")
    kwargs: dict[str, Any] = {"verbose": verbose or None}
    if language:
        kwargs["language"] = language

    try:
        result = model.transcribe(str(audio_path), **kwargs)
    except torch.cuda.OutOfMemoryError as exc:
        raise WhispererError(
            f"CUDA out of memory during transcription with '{model_name}'. Try a smaller model."
        ) from exc
    except Exception as exc:
        raise WhispererError(f"Transcription failed for {audio_path}: {exc}") from exc
    finally:
        del model
        _empty_cuda_cache(torch)

    log(f"Done. Detected language: {result.get('language', '?')}")
    return result


def expanded_output_formats(output_format: str) -> tuple[str, ...]:
    if output_format not in OUTPUT_FORMATS:
        raise WhispererError(
            f"Unsupported output format '{output_format}'. Supported: {', '.join(OUTPUT_FORMATS)}."
        )
    if output_format == "all":
        return WRITER_FORMATS
    return (output_format,)


def output_paths(source_path: Path, output_dir: Path, output_format: str) -> tuple[Path, ...]:
    return tuple(output_dir / f"{source_path.stem}.{fmt}" for fmt in expanded_output_formats(output_format))


def write_output(
    result: Mapping[str, Any],
    source_path: Path,
    output_dir: Path,
    output_format: str,
) -> tuple[Path, ...]:
    try:
        from whisper.utils import get_writer
    except ImportError as exc:
        raise WhispererError("Missing Whisper writer dependency. Install openai-whisper.") from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    writer = get_writer(output_format, str(output_dir))
    writer(dict(result), str(source_path))
    files = output_paths(source_path, output_dir, output_format)

    if output_format == "all":
        log(f"Output written to {output_dir}/ (all formats)")
    else:
        log(f"Output written to {files[0]}")
    return files


def validate_options(options: TranscriptionOptions) -> None:
    if not options.input_path.exists():
        raise WhispererError(f"File not found: {options.input_path}")
    if not is_supported(options.input_path):
        raise WhispererError(
            f"Unsupported input format '{options.input_path.suffix}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
        )
    if options.output_dir.exists() and not options.output_dir.is_dir():
        raise WhispererError(f"Output path is not a directory: {options.output_dir}")
    if options.model not in MODELS:
        raise WhispererError(f"Unsupported model '{options.model}'. Supported: {', '.join(MODELS)}.")
    if options.output_format not in OUTPUT_FORMATS:
        raise WhispererError(
            f"Unsupported output format '{options.output_format}'. Supported: {', '.join(OUTPUT_FORMATS)}."
        )


def run_pipeline(
    options: TranscriptionOptions,
    *,
    dependency_checker: Callable[[], None] = check_dependencies,
    runner: Runner = subprocess.run,
    transcriber: Transcriber = transcribe_audio,
    writer: Writer = write_output,
) -> PipelineResult:
    validate_options(options)
    dependency_checker()

    kept_intermediate: Path | None = None
    with tempfile.TemporaryDirectory(prefix="whisperer_") as tmp:
        audio_path = prepare_audio(options.input_path, Path(tmp), runner)
        transcription = transcriber(audio_path, options.model, options.language, options.verbose)
        try:
            output_files = writer(
                transcription,
                options.input_path,
                options.output_dir,
                options.output_format,
            )
        except WhispererError:
            raise
        except Exception as exc:
            raise WhispererError(
                f"Could not write output for {options.input_path} to {options.output_dir}: {exc}"
            ) from exc

        if options.keep_intermediate and audio_path != options.input_path:
            options.output_dir.mkdir(parents=True, exist_ok=True)
            kept_intermediate = options.output_dir / audio_path.name
            shutil.copy2(audio_path, kept_intermediate)
            log(f"Intermediate audio kept: {kept_intermediate}")

    return PipelineResult(
        output_dir=options.output_dir,
        output_files=output_files,
        kept_intermediate=kept_intermediate,
        detected_language=str(transcription.get("language")) if transcription.get("language") else None,
        transcription=transcription,
    )
