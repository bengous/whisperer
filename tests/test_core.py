from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from whisperer.core import (
    TranscriptionOptions,
    WhispererError,
    build_ffmpeg_command,
    build_ffprobe_command,
    is_supported,
    is_video,
    needs_conversion,
    output_paths,
    run_pipeline,
)


class CoreTests(unittest.TestCase):
    def test_extension_detection(self) -> None:
        self.assertTrue(is_video(Path("meeting.MP4")))
        self.assertTrue(is_supported(Path("audio.aac")))
        self.assertFalse(is_supported(Path("notes.md")))

    def test_ffmpeg_command_targets_whisper_ready_wav(self) -> None:
        self.assertEqual(
            build_ffmpeg_command(Path("in.mp4"), Path("out.wav")),
            [
                "ffmpeg",
                "-y",
                "-i",
                "in.mp4",
                "-vn",
                "-acodec",
                "pcm_s16le",
                "-ar",
                "16000",
                "-ac",
                "1",
                "out.wav",
            ],
        )

    def test_wav_probe_controls_conversion(self) -> None:
        calls: list[list[str]] = []

        def runner(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
            calls.append(cmd)
            stdout = json.dumps(
                {"streams": [{"codec_name": "pcm_s16le", "sample_rate": "16000", "channels": 1}]}
            )
            return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

        self.assertFalse(needs_conversion(Path("ready.wav"), runner))
        self.assertEqual(calls, [build_ffprobe_command(Path("ready.wav"))])

    def test_output_paths_expand_all_formats(self) -> None:
        self.assertEqual(
            output_paths(Path("clip.mp4"), Path("out"), "all"),
            (
                Path("out/clip.txt"),
                Path("out/clip.srt"),
                Path("out/clip.json"),
                Path("out/clip.vtt"),
                Path("out/clip.tsv"),
            ),
        )

    def test_pipeline_video_uses_fakes_and_original_output_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "clip.mp4"
            output_dir = root / "outputs"
            input_path.write_text("fake video", encoding="utf-8")
            commands: list[list[str]] = []
            writer_calls: list[tuple[Path, Path, str]] = []

            def runner(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                commands.append(cmd)
                Path(cmd[-1]).write_text("fake wav", encoding="utf-8")
                return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

            def transcriber(
                audio_path: Path,
                model_name: str,
                language: str | None,
                verbose: bool,
            ) -> dict[str, object]:
                self.assertEqual(audio_path.suffix, ".wav")
                self.assertEqual(model_name, "tiny")
                self.assertEqual(language, "fr")
                self.assertFalse(verbose)
                return {"text": "bonjour", "language": "fr", "segments": []}

            def writer(
                result: object,
                source_path: Path,
                output_path: Path,
                output_format: str,
            ) -> tuple[Path, ...]:
                writer_calls.append((source_path, output_path, output_format))
                output_path.mkdir()
                target = output_path / f"{source_path.stem}.{output_format}"
                target.write_text("bonjour", encoding="utf-8")
                return (target,)

            result = run_pipeline(
                TranscriptionOptions(
                    input_path=input_path,
                    output_dir=output_dir,
                    model="tiny",
                    language="fr",
                    output_format="srt",
                ),
                dependency_checker=lambda: None,
                runner=runner,
                transcriber=transcriber,
                writer=writer,
            )

            self.assertEqual(result.output_files, (output_dir / "clip.srt",))
            self.assertEqual(writer_calls, [(input_path, output_dir, "srt")])
            self.assertEqual(commands[0][0], "ffmpeg")
            self.assertIn(str(input_path), commands[0])

    def test_missing_input_is_user_facing_error(self) -> None:
        with self.assertRaisesRegex(WhispererError, "File not found"):
            run_pipeline(TranscriptionOptions(input_path=Path("missing.wav")), dependency_checker=lambda: None)

    def test_output_path_must_be_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.wav"
            output_path = root / "not-a-dir"
            input_path.write_text("fake wav", encoding="utf-8")
            output_path.write_text("not a directory", encoding="utf-8")

            with self.assertRaisesRegex(WhispererError, "Output path is not a directory"):
                run_pipeline(
                    TranscriptionOptions(input_path=input_path, output_dir=output_path),
                    dependency_checker=lambda: None,
                )

    def test_pipeline_wraps_writer_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_path = root / "input.wav"
            input_path.write_text("fake wav", encoding="utf-8")

            def runner(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
                stdout = json.dumps(
                    {"streams": [{"codec_name": "pcm_s16le", "sample_rate": "16000", "channels": 1}]}
                )
                return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")

            def transcriber(
                audio_path: Path,
                model_name: str,
                language: str | None,
                verbose: bool,
            ) -> dict[str, object]:
                return {"text": "bonjour", "language": "fr", "segments": []}

            def writer(
                result: object,
                source_path: Path,
                output_path: Path,
                output_format: str,
            ) -> tuple[Path, ...]:
                raise PermissionError("read-only output directory")

            with self.assertRaisesRegex(WhispererError, "Could not write output"):
                run_pipeline(
                    TranscriptionOptions(input_path=input_path, output_dir=root / "outputs"),
                    dependency_checker=lambda: None,
                    runner=runner,
                    transcriber=transcriber,
                    writer=writer,
                )


if __name__ == "__main__":
    unittest.main()
