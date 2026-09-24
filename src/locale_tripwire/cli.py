"""CLI for detecting ambiguous JSON object keys."""

from __future__ import annotations

import argparse
import json
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def turkish_lower(value: str) -> str:
    """Lowercase with the Turkish dotted/dotless I mapping.

    This is a focused collision heuristic, not a full Unicode locale engine.
    """
    # A decomposed capital dotted I must not become dotless i + combining dot.
    value = value.replace("I\u0307", "i")
    return value.translate(str.maketrans({"I": "ı", "İ": "i"})).lower()


def collision_keys(value: str) -> dict[str, str]:
    normalized = unicodedata.normalize("NFC", value)
    return {
        "nfc": normalized,
        "casefold": unicodedata.normalize("NFC", normalized.casefold()),
        "tr-lower": unicodedata.normalize("NFC", turkish_lower(normalized)),
    }


@dataclass
class JSONObject:
    pairs: list[tuple[str, Any]]


def inspect_pairs(pairs: list[tuple[str, Any]], location: str, findings: list[dict[str, str]]) -> None:
    seen_exact: set[str] = set()
    seen: dict[str, dict[str, str]] = {rule: {} for rule in ("nfc", "casefold", "tr-lower")}
    for key, _value in pairs:
        if key in seen_exact:
            findings.append({"path": location, "rule": "duplicate", "first": key, "second": key})
        seen_exact.add(key)
        for rule, folded in collision_keys(key).items():
            first = seen[rule].get(folded)
            if first is not None and first != key:
                findings.append({"path": location, "rule": rule, "first": first, "second": key})
            else:
                seen[rule][folded] = key



def inspect_json(source: str) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    parsed = json.loads(source, object_pairs_hook=JSONObject)

    def walk(node: Any, location: str) -> None:
        if isinstance(node, JSONObject):
            pairs = node.pairs
            inspect_pairs(pairs, location, findings)
            for key, child in pairs:
                walk(child, f"{location}.{key}" if location else key)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{location}[{index}]")

    walk(parsed, "$")
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find JSON keys that collide after Unicode normalization or case conversion.")
    parser.add_argument("files", nargs="+", type=Path, help="JSON files to inspect")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)

    findings: list[dict[str, str]] = []
    errors: list[str] = []
    for path in args.files:
        try:
            source = path.read_text(encoding="utf-8")
            for finding in inspect_json(source):
                findings.append({"file": str(path), **finding})
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            errors.append(f"{path}: {exc}")

    if args.format == "json":
        print(json.dumps({"findings": findings, "errors": errors}, ensure_ascii=False, indent=2))
    else:
        for item in findings:
            print(f"{item['file']}:{item['path']}: {item['rule']}: {item['first']!r} <> {item['second']!r}")
        for error in errors:
            print(error, file=sys.stderr)
        if not findings and not errors:
            print("No key collisions found.")
    return 2 if errors else 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
