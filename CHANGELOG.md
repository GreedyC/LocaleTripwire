# Changelog

## Unreleased

- Select rules and error/warning severities with configurable failure thresholds.
- Report both key positions, Unicode code points and their shared transformation.
- Scan directories with include/exclude patterns and deterministic deduplication.
- Add escaped GitHub Actions annotations and a duplicate-only pre-commit hook.
- Verify wheel/sdist installation and real hook execution on Windows, Linux and
  macOS with Python 3.10 and 3.14. Prepare a manual, gated OIDC publishing workflow.
- Keep existing rules enabled at error severity by default; JSON diagnostic fields
  are additive. Directory scans with no matching files return exit code 2.

No PyPI release is implied by this changelog.
