"""CLI for detecting ambiguous JSON object keys."""

from __future__ import annotations

import argparse
import bisect
import fnmatch
import json
import os
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
    pairs: list[tuple[str, Any, int]]


RULES = ("duplicate", "nfc", "casefold", "tr-lower")
DEFAULT_EXCLUDES = (".git", "node_modules", ".venv", "venv", "__pycache__")


class PositionedJSON:
    """Read an already validated JSON document without losing key offsets."""

    def __init__(self, source: str):
        self.source = source
        self.offset = 0
        self.decoder = json.JSONDecoder()

    def space(self) -> None:
        while self.offset < len(self.source) and self.source[self.offset] in " \t\r\n":
            self.offset += 1

    def read(self) -> Any:
        self.space()
        char = self.source[self.offset]
        if char not in "{[":
            value, self.offset = self.decoder.raw_decode(self.source, self.offset)
            return value
        self.offset += 1
        self.space()
        closing = "}" if char == "{" else "]"
        items = []
        while self.source[self.offset] != closing:
            if char == "{":
                start = self.offset
                key, self.offset = self.decoder.raw_decode(self.source, self.offset)
                self.space()
                self.offset += 1  # colon; syntax was validated before this pass
                items.append((key, self.read(), start))
            else:
                items.append(self.read())
            self.space()
            if self.source[self.offset] == closing:
                break
            self.offset += 1  # comma
            self.space()
        self.offset += 1
        return JSONObject(items) if char == "{" else items


class NonStandardJSONConstant(ValueError):
    """Raised for Python-only JSON constants such as NaN."""


def reject_constant(value: str) -> None:
    raise NonStandardJSONConstant(f"non-standard JSON constant: {value}")


def inspect_json(
    source: str,
    rules: tuple[str, ...] = RULES,
    severities: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Report collisions; existing fields remain alongside additive diagnostics."""
    if not rules or any(rule not in RULES for rule in rules):
        raise ValueError("rules must contain known rule names")
    severities = severities or {}
    if any(rule not in RULES or level not in ("error", "warning")
           for rule, level in severities.items()):
        raise ValueError("invalid rule severity")
    findings: list[dict[str, Any]] = []
    json.loads(source, parse_constant=reject_constant)
    parsed = PositionedJSON(source).read()
    line_starts = [0] + [index + 1 for index, char in enumerate(source) if char == "\n"]

    def position(offset: int) -> dict[str, int]:
        line = bisect.bisect_right(line_starts, offset)
        return {"line": line, "column": offset - line_starts[line - 1] + 1}

    def codepoints(key: str) -> list[str]:
        return [f"U+{ord(char):04X} {unicodedata.name(char, 'UNNAMED')}" for char in key]

    def walk(node: Any, location: str) -> None:
        if isinstance(node, JSONObject):
            pairs = node.pairs
            seen: dict[str, dict[str, tuple[str, int]]] = {rule: {} for rule in rules}
            for key, _child, offset in pairs:
                transformed = {"duplicate": key, **collision_keys(key)}
                for rule in rules:
                    folded = transformed[rule]
                    first = seen[rule].get(folded)
                    if first is not None and (rule == "duplicate" or first[0] != key):
                        findings.append({
                            "path": location, "rule": rule,
                            "first": first[0], "second": key,
                            "severity": severities.get(rule, "error"),
                            "first_position": position(first[1]),
                            "second_position": position(offset),
                            "first_codepoints": codepoints(first[0]),
                            "second_codepoints": codepoints(key),
                            "transformed": folded,
                        })
                    elif first is None:
                        seen[rule][folded] = (key, offset)
            for key, child, _offset in pairs:
                walk(child, f"{location}[{json.dumps(key, ensure_ascii=True)}]")
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{location}[{index}]")

    walk(parsed, "$")
    return findings


def collect_files(
    inputs: list[Path], excludes: list[str], includes: list[str],
) -> tuple[list[Path], list[str]]:
    """Expand directories deterministically; never follow directory symlinks."""
    files: list[Path] = []
    errors: list[str] = []
    seen: set[Path] = set()

    def excluded(path: Path, root: Path) -> bool:
        relative = path.relative_to(root).as_posix()
        return any(fnmatch.fnmatchcase(relative, pattern)
                   or fnmatch.fnmatchcase(path.name, pattern) for pattern in excludes)

    def add(path: Path) -> None:
        try:
            resolved = path.resolve()
        except (OSError, RuntimeError) as exc:
            errors.append(f"{path}: {exc}")
            return
        if resolved not in seen:
            files.append(path)
            seen.add(resolved)

    for root in inputs:
        if not root.is_dir():
            add(root)  # explicit files are checked regardless of glob/exclusion
            continue
        matched = 0
        def onerror(exc: OSError) -> None:
            errors.append(str(exc))
        for current, dirs, names in os.walk(root, followlinks=False, onerror=onerror):
            directory = Path(current)
            dirs[:] = sorted(name for name in dirs
                             if not excluded(directory / name, root)
                             and not (directory / name).is_symlink())
            for name in sorted(names):
                path = directory / name
                relative = path.relative_to(root).as_posix()
                if (not path.is_symlink() and not excluded(path, root)
                        and any(fnmatch.fnmatchcase(relative, pattern)
                                or fnmatch.fnmatchcase(name, pattern) for pattern in includes)):
                    add(path)
                    matched += 1
        if not matched:
            errors.append(f"{root}: no matching files found")
    return files, errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Find JSON keys that collide after Unicode normalization or case conversion.")
    parser.add_argument("files", nargs="+", type=Path, help="JSON files or directories to inspect")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--rules", default=",".join(RULES), help="Comma-separated rules: " + ", ".join(RULES))
    parser.add_argument("--severity", action="append", default=[], metavar="RULE=LEVEL",
                        help="Set a rule to error or warning; repeat for multiple rules")
    parser.add_argument("--fail-on", choices=("error", "warning"), default="error",
                        help="Failure threshold; warning includes both levels")
    parser.add_argument("--include", action="append", metavar="GLOB",
                        help="Directory file pattern (repeatable; default: *.json)")
    parser.add_argument("--exclude", action="append", default=[], metavar="GLOB",
                        help="Exclude directory entries by basename or root-relative glob")
    args = parser.parse_args(argv)
    rules = tuple(dict.fromkeys(rule.strip() for rule in args.rules.split(",")))
    if any(rule not in RULES for rule in rules):
        parser.error("--rules contains an empty or unknown rule")
    severities = {}
    for assignment in args.severity:
        rule, separator, level = assignment.partition("=")
        if not separator or rule not in rules or level not in ("error", "warning"):
            parser.error("--severity must be an enabled RULE=error or RULE=warning")
        severities[rule] = level
    files, errors = collect_files(args.files, [*DEFAULT_EXCLUDES, *args.exclude], args.include or ["*.json"])
    findings: list[dict[str, Any]] = []
    for path in files:
        try:
            source = path.read_text(encoding="utf-8")
            for finding in inspect_json(source, rules, severities):
                findings.append({"file": str(path), **finding})
        except (OSError, UnicodeError, json.JSONDecodeError, NonStandardJSONConstant, RecursionError) as exc:
            errors.append(f"{path}: {exc}")

    if args.format == "json":
        print(json.dumps({"findings": findings, "errors": errors}, ensure_ascii=True, indent=2))
    else:
        for item in findings:
            first, second = item["first_position"], item["second_position"]
            # ASCII escaping keeps redirected Windows output and lone surrogates safe.
            label = json.dumps(item["file"], ensure_ascii=True)
            print(f"{label}:{second['line']}:{second['column']}: {item['severity']} {item['rule']} "
                  f"at {item['path']}: {ascii(item['first'])} <> {ascii(item['second'])}")
            print(f"  first key: {first['line']}:{first['column']}; "
                  f"shared transformed key: {ascii(item['transformed'])}")
            print("  first: " + "; ".join(item["first_codepoints"]))
            print("  second: " + "; ".join(item["second_codepoints"]))
        for error in errors:
            print(error.encode("ascii", "backslashreplace").decode("ascii"), file=sys.stderr)
        if not findings and not errors:
            print("No key collisions found.")
    failed = any(item["severity"] == "error" or args.fail_on == "warning" for item in findings)
    return 2 if errors else 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
