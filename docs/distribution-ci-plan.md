# Distribution and CI integration plan

Status: installation verification scripts, pre-commit hook, GitHub annotations and
the six-job cross-platform CI workflow and manual OIDC publisher are implemented. The usage guide is
[ci-usage.md](ci-usage.md). Actual runner results must be checked at the pushed
commit before release; PyPI publication still requires owner-side setup.

## Goal

Make installation and automated checks easy without a runtime dependency or a
custom GitHub Action to maintain. Preserve rule selection, severity and exit codes.

## 1. Packaging and installation

- Build a wheel and source distribution in a clean environment; install each into
  an empty environment and smoke-test the installed `locale-tripwire` command.
- Validate package metadata and README rendering with `twine check`.
- Choose the next release version only after verification. Check availability and
  ownership of the PyPI name before promising `pip install locale-tripwire`.
- Document `pipx` and isolated virtualenv installation; never require sudo or
  bypass externally-managed Python protections.
- Publish with PyPI Trusted Publishing after the repository owner configures the
  publisher. No API token in source, logs or this plan; no automatic publication
  until that setup and release approval are complete.

## 2. pre-commit

- Add `.pre-commit-hooks.yaml` with a Python hook and a JSON file filter.
- Supply explicit `--rules duplicate` in the suggested configuration; users may
  opt into consumer-specific rules and warning levels.
- Smoke-test an actual temporary Git repository using the hook at a pinned tag.
  Verify clean input, collision, invalid JSON and filenames containing spaces.
- Clarify that pre-commit passes changed files only, while directory scanning can
  cover an entire catalog. Document bypass behavior for explicit file arguments.

## 3. GitHub Actions consumption

- Start with a reusable README workflow example, not a marketplace action.
- Use read-only permissions and install a pinned released version in an isolated
  environment. Execute chosen rules on repository-owned JSON catalogs.
- For annotations, consume JSON diagnostics and escape workflow command data and
  properties (percent, CR/LF, colon/comma where applicable). Validate paths relative
  to the checked-out repository. Never emit untrusted keys as raw workflow commands.
- Use `second_position` for the annotation location and include the first key's
  position in the message. Warning-only runs succeed; input errors fail.

## Acceptance gates before release

- Existing full test suite plus installation and hook smoke tests pass.
- Real GitHub jobs pass on Linux, macOS and Windows, on Python 3.10 and 3.14.
  Local cp1252 tests are helpful but do not prove Windows filesystem behavior.
- Test CRLF, Unicode filenames, path separators, warning thresholds and invalid
  input in the installed package, not only with `PYTHONPATH=src`.
- Test source/wheel contents, absence of private data and accidental dependencies.
- English/Turkish docs match the tested commands; changelog explains additive JSON
  fields and backward-compatible default severities.

## Remaining release steps

1. Check the pushed commit's full cross-platform CI; repair any failed job.
2. Have the owner configure the PyPI project and Trusted Publisher.
3. Select the release version, create a matching immutable tag, then dispatch
   `publish.yml`. It re-runs the six jobs before allowing a separate publishing job.

No scheduled task or PyPI publication is created by this document.
