"""Build-artifact install and real CLI verification on Windows, macOS and Linux."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv


def run(args: list[str], cwd: Path, expected: int = 0) -> subprocess.CompletedProcess:
    result = subprocess.run(args, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode != expected:
        raise AssertionError(f"{args!r}: exit {result.returncode}, expected {expected}\n"
                             f"{result.stdout}\n{result.stderr}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    artifact = args.artifact.resolve()
    repo = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="locale-install-") as folder:
        root = Path(folder)
        environment = root / "env"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        cli = environment / ("Scripts/locale-tripwire.exe" if os.name == "nt" else "bin/locale-tripwire")
        run([str(python), "-m", "pip", "install", "--no-deps", str(artifact)], root)
        run([str(python), "-m", "unittest", "discover", "-s", str(repo / "tests"), "-v"], root)
        catalog = root / "catalog with spaces"
        catalog.mkdir()
        clean = catalog / "clean.json"
        clean.write_text('{"title":"Hello"}', encoding="utf-8")
        run([str(cli), str(catalog)], root)
        duplicate = catalog / "ş-key.json"
        duplicate.write_bytes(b'{\r\n  "a":1,\r\n  "a":2\r\n}')
        result = run([str(cli), str(catalog), "--rules", "duplicate", "--format", "json"], root, 1)
        import json
        report = json.loads(result.stdout)
        assert report["findings"][0]["second_position"] == {"line": 3, "column": 3}
        run([str(cli), str(catalog), "--rules", "duplicate", "--severity", "duplicate=warning"], root)
        run([str(cli), str(catalog), "--exclude", "ş-key.json"], root)
        run([str(cli), str(duplicate), "--rules", "duplicate", "--format", "github",
             "--annotation-root", str(root)], root, 1)
        clean.write_text('{', encoding="utf-8")
        run([str(cli), str(clean)], root, 2)
    print(f"Verified {artifact.name}: installed tests and CLI smoke checks")


if __name__ == "__main__":
    main()
