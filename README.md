# LocaleTripwire

[Türkçe README](README.tr.md)

LocaleTripwire is a small, offline command-line tool for spotting ambiguous keys in UTF-8 JSON files. It detects exact duplicate keys and pairs that become equal after Unicode NFC normalization, case folding, or a focused Turkish lowercase conversion. It reports the containing object path and changes no input files.

The practical problem is real: [duplicate keys can break translation-file imports](https://opswat.developerhub.io/docs/mdmft/v3.11.3/knowledge-base/why-do-i-receive--localization-file-has-xxx-keys-but-your-transl), while [Unicode normalization](https://unicode.org/faq/normalization.html) and [Turkish casing](https://github.com/jeancroy/fuzz-aldrin-plus/issues/33) can make visually or logically related strings compare differently across systems. This tool is a focused preflight check, not a replacement for a full localization linter such as [li18nt](https://github.com/simonwep/li18nt).

## Install

For isolated `pipx`/virtualenv installation, pre-commit and safe GitHub Actions
annotations, see [installation and automation](docs/ci-usage.md). PyPI publication
is not yet verified; install from a checked-out revision.

Python 3.10 or later is required. From this repository:

```sh
python3 -m pip install -e .
```

## Use

```sh
locale-tripwire messages.json
locale-tripwire --format json messages.json config.json
locale-tripwire locales/ --exclude generated --exclude 'drafts/*.json'
locale-tripwire locales/ --rules duplicate,nfc --severity nfc=warning
locale-tripwire locales/ --rules casefold --severity casefold=warning --fail-on warning
```

Example input:

```json
{"ISIK": "light", "ısık": "another value"}
```

This pair triggers the `tr-lower` rule. `{"Name": 1, "name": 2}` triggers `casefold`. Distinct spellings of `café` using composed and decomposed characters trigger `nfc`. A pair may appear under more than one rule.

### Rules and severity

`--rules` selects a comma-separated subset of `duplicate,nfc,casefold,tr-lower`.
All rules remain enabled at `error` severity by default for backward compatibility.
Use repeatable `--severity RULE=warning` or `RULE=error` overrides for enabled rules.
Warnings are still reported but do not fail the command unless `--fail-on warning`
is set. For consumers that compare JSON keys exactly, start with `--rules duplicate`;
enable other rules only when their transformations matter to your consumer.

Exit codes: `0` no findings at the failure threshold, `1` findings at the threshold,
`2` unreadable or invalid input (including non-standard `NaN`/`Infinity`) or a directory
with no matching files. Input errors take precedence over findings. Invalid options
also exit with `2`.

### Actionable diagnostics

Each finding reports the containing object path (for example `$["items"][0]`),
both keys' opening-quote positions, Unicode code points and names, and the shared
transformed key. Lines and columns are **1-based character positions**, not byte
offsets; an escaped key points to its original opening quote. Text diagnostics escape
non-ASCII/control characters to work in redirected terminals, including Windows.

JSON output retains `findings` and `errors`, and each finding's `file`, `path`, `rule`,
`first`, and `second`. Additive fields are `severity`, `first_position`,
`second_position` (each with `line` and `column`), `first_codepoints`,
`second_codepoints`, and `transformed`.

`--format github` emits escaped GitHub Actions annotations. The default annotation
root is the current directory; use `--annotation-root PATH` when needed.

### Directory scanning

Directories are searched recursively and deterministically for `*.json` files.
Repeat `--include GLOB` to replace that default with your own file patterns.
Repeat `--exclude GLOB` to omit entries by basename or root-relative path.
Quote globs so your shell does not expand them. Matching is case-sensitive on every
platform, uses forward-slash paths, and follows Python `fnmatch` semantics (not gitignore;
`*` can match `/`). Excluding a directory prunes its entire subtree.

`.git`, `node_modules`, `.venv`, `venv`, and `__pycache__` are always skipped during
directory discovery, as are symlinks. Overlapping inputs are deduplicated by resolved
path. Explicit file inputs bypass include/exclude filters and can be symlinks;
explicit directory inputs are always scanned. Files are never modified.

## What the result means

JSON keys are normally distinct unless they match exactly. A non-duplicate finding is a **potential interoperability hazard**, not proof that a specific application merges the keys. LocaleTripwire does not implement full CLDR locale rules, confusable-character detection, JSON Schema validation, translation quality checks, or automatic renaming. The Turkish rule covers dotted/dotless I and regular lowercase as a targeted heuristic.

The tool reads local UTF-8 files only and does not send their contents to any service. Do not publish private catalogs or API payloads in issues; use minimal synthetic examples.

## Development and contributions

```sh
python3 -m unittest discover -s tests -v
```

Please open an issue with a minimal JSON example, the runtime or consumer where it matters, and expected behavior. Contributions that reduce false positives or document real-world cases are especially useful.

MIT licensed; see [LICENSE](LICENSE).
