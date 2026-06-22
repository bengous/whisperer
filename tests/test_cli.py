from __future__ import annotations

import unittest
from pathlib import Path

from whisperer.__main__ import options_from_args, parse_args


class CliTests(unittest.TestCase):
    def test_parse_args_builds_transcription_options(self) -> None:
        args = parse_args(
            [
                "meeting.mp4",
                "--model",
                "base",
                "--language",
                "fr",
                "--format",
                "vtt",
                "--output-dir",
                "results",
                "--keep-intermediate",
            ]
        )

        options = options_from_args(args)

        self.assertEqual(options.input_path, Path("meeting.mp4"))
        self.assertEqual(options.model, "base")
        self.assertEqual(options.language, "fr")
        self.assertEqual(options.output_format, "vtt")
        self.assertEqual(options.output_dir, Path("results"))
        self.assertTrue(options.keep_intermediate)


if __name__ == "__main__":
    unittest.main()
