# Release Checklist

Whisperer is not published yet.

Before a public release:

1. Confirm the public package name. Current local distribution name is
   `whisperer-local`.
2. Start from a clean git status where `.gitignore` excludes local media,
   outputs, caches, `.venv/`, `.agents/`, `plans/`, and `skills-lock.json`.
3. Run:

   ```bash
   bash scripts/check.sh
   python -m pip install -e .
   whisperer --help
   whisperer-web --help
   ```

4. Optionally run one manual smoke test on a tiny non-sensitive media file.
5. Review the publishable file list:

   ```bash
   git status --short
   git ls-files
   ```

Do not publish to PyPI, create a remote GitHub repository, push, or delete local
media without an explicit human request.
