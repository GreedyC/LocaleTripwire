# LocaleTripwire

[Türkçe README](README.tr.md)

LocaleTripwire is a small, offline command-line tool for spotting ambiguous keys in UTF-8 JSON files. It detects exact duplicate keys and pairs that become equal after Unicode NFC normalization, case folding, or a focused Turkish lowercase conversion. It reports the containing object path and changes no input files.

The practical problem is real: [duplicate keys can break translation-file imports](https://opswat.developerhub.io/docs/mdmft/v3.11.3/knowledge-base/why-do-i-receive--localization-file-has-xxx-keys-but-your-transl), while [Unicode normalization](https://unicode.org/faq/normalization.html) and [Turkish casing](https://github.com/jeancroy/fuzz-aldrin-plus/issues/33) can make visually or logically related strings compare differently across systems. This tool is a focused preflight check, not a replacement for a full localization linter such as [li18nt](https://github.com/simonwep/li18nt).

## Install

Python 3.10 or later is required. From this repository:

```sh
python3 -m pip install -e .
```

## Use

```sh
locale-tripwire messages.json
locale-tripwire --format json messages.json config.json
```

Example input:

```json
{"ISIK": "light", "ısık": "another value"}
```

This pair triggers the `tr-lower` rule. `{"Name": 1, "name": 2}` triggers `casefold`. Distinct spellings of `café` using composed and decomposed characters trigger `nfc`. A pair may appear under more than one rule.

Exit codes: `0` no findings, `1` one or more collisions, `2` unreadable or invalid input (including non-standard `NaN`/`Infinity`). JSON output includes `findings` and `errors`, so CI can consume it without parsing human text. Paths point to the containing JSON object using unambiguous bracket notation, for example `$["items"][0]`.

## What the result means

JSON keys are normally distinct unless they match exactly. A non-duplicate finding is a **potential interoperability hazard**, not proof that a specific application merges the keys. LocaleTripwire does not implement full CLDR locale rules, confusable-character detection, JSON Schema validation, translation quality checks, or automatic renaming. The Turkish rule covers dotted/dotless I and regular lowercase as a targeted heuristic.

The tool reads local UTF-8 files only and does not send their contents to any service. Do not publish private catalogs or API payloads in issues; use minimal synthetic examples.

## Development and contributions

```sh
python3 -m unittest discover -s tests -v
```

Please open an issue with a minimal JSON example, the runtime or consumer where it matters, and expected behavior. Contributions that reduce false positives or document real-world cases are especially useful.

MIT licensed; see [LICENSE](LICENSE).
