from __future__ import annotations

import unittest

from flask import render_template

from whisperer.core import DEFAULT_MODEL, MODELS, OUTPUT_FORMATS
from whisperer.web import create_app

SAMPLE_RESULT = {
    "text": "Bonjour, ceci est un test.",
    "segments": [
        {"start": "0:00", "end": "0:03", "text": "Bonjour,"},
        {"start": "0:03", "end": "0:06", "text": "ceci est un test."},
    ],
    "language": "fr",
    "model": "turbo",
    "format": "srt",
    "files": ["sample.srt"],
}


def _render(**context: object) -> str:
    app = create_app()
    base = {
        "models": MODELS,
        "formats": OUTPUT_FORMATS,
        "default_model": DEFAULT_MODEL,
        "default_format": "srt",
        "error": None,
        "result": None,
    }
    base.update(context)
    with app.test_request_context():
        return render_template("index.html", **base)


class WebIndexTests(unittest.TestCase):
    def test_get_index_returns_form_and_local_first_framing(self) -> None:
        client = create_app().test_client()

        response = client.get("/")

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('name="file"', body)
        self.assertIn('name="model"', body)
        self.assertIn('name="language"', body)
        self.assertIn('name="format"', body)
        self.assertIn("Runs locally", body)
        for model in MODELS:
            self.assertIn(f'value="{model}"', body)

    def test_default_model_and_format_are_preselected(self) -> None:
        body = _render()

        self.assertIn(f'value="{DEFAULT_MODEL}" selected', body)
        self.assertIn('value="srt" selected', body)

    def test_error_state_renders_message(self) -> None:
        body = _render(error="No file selected.")

        self.assertIn('role="alert"', body)
        self.assertIn("No file selected.", body)

    def test_result_state_renders_text_segments_and_downloads(self) -> None:
        body = _render(result=SAMPLE_RESULT)

        self.assertIn("Bonjour, ceci est un test.", body)
        self.assertIn("0:00", body)
        self.assertIn("ceci est un test.", body)
        self.assertIn("/outputs/sample.srt", body)
        self.assertIn("/download/sample.srt", body)
        self.assertIn("Language", body)
        self.assertIn("fr", body)


if __name__ == "__main__":
    unittest.main()
