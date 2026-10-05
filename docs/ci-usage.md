# Installation and automation

Python 3.10+ is supported on Windows, macOS and Linux. No runtime dependencies,
account or network access is needed for scanning. Installation tools download the
package and their own dependencies.

## Isolated installation

From a checked-out revision:

```sh
pipx install .
locale-tripwire --help
```

Or create a virtual environment with `python -m venv .venv`, then use
`.venv/bin/python -m pip install .` on macOS/Linux or
`.venv\Scripts\python.exe -m pip install .` on Windows. The command lives in the
same `bin`/`Scripts` directory. No sudo or system-Python override is needed.

There is no verified PyPI publication yet; do not use `pip install locale-tripwire`
until the release is actually published. Pin an audited Git revision or install
a wheel built from that revision instead.

## pre-commit

Use an immutable commit or published tag that contains `.pre-commit-hooks.yaml`:

```yaml
repos:
  - repo: https://github.com/GreedyC/LocaleTripwire
    rev: REPLACE_WITH_VERIFIED_COMMIT_OR_TAG
    hooks:
      - id: locale-tripwire
        # Default: duplicate only. Enable additional consumer-specific rules:
        args: [--rules, 'duplicate,nfc', --severity, 'nfc=warning']
```

Install pre-commit in an isolated environment, then run `pre-commit install` and
`pre-commit run --all-files`. The hook receives selected JSON filenames, not a full
directory scan. Explicit filenames bypass directory-discovery exclusions; use
pre-commit's own `exclude` setting for generated files. Warnings remain visible
but succeed unless `--fail-on warning` is added.

## GitHub Actions

This example installs an audited Git revision; replace the placeholder before use.
The consuming repository must contain the `locales/` directory and matching files.

```yaml
name: JSON key check
on: [push, pull_request]
permissions:
  contents: read
jobs:
  keys:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - run: python -m pip install 'git+https://github.com/GreedyC/LocaleTripwire.git@REPLACE_WITH_VERIFIED_COMMIT'
      - run: locale-tripwire locales/ --rules duplicate,nfc --severity nfc=warning --format github
```

`--format github` emits escaped error/warning annotations at the second key's
position. Messages include the first position and transformation. Paths are
repository-relative to the current directory, or `--annotation-root PATH`.
Findings outside that root have no clickable file annotation; their message is
still reported. Untrusted paths/messages are escaped, and UTF-8 is used for this
format even in redirected Windows consoles. Exit codes are unchanged: 0 below
threshold, 1 threshold findings, 2 invalid/unreadable input or no matching files.

## Release gate

The repository workflow builds wheel/sdist, runs `twine check`, installs both
artifacts into clean environments and tests the real hook. All six combinations
of Linux/macOS/Windows and Python 3.10/3.14 must pass before release. See
[distribution-ci-plan.md](distribution-ci-plan.md) for the PyPI owner-setup gate.
