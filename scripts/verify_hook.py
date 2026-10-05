"""Exercise the real pre-commit hook from the current Git revision."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile


def run(args: list[str], cwd: Path, expected: int = 0) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace")
    if result.returncode != expected:
        raise AssertionError(f"{args!r}: exit {result.returncode}\n{result.stdout}\n{result.stderr}")
    return result.stdout + result.stderr


def main() -> None:
    repo = Path(__file__).resolve().parents[1]
    revision = run(["git", "rev-parse", "HEAD"], repo).strip()
    with tempfile.TemporaryDirectory(prefix="locale-hook-") as folder:
        root = Path(folder)
        run(["git", "init"], root)
        # JSON is also valid YAML; avoids a dependency merely to write the config.
        config = {"repos": [{"repo": repo.as_uri(), "rev": revision,
                             "hooks": [{"id": "locale-tripwire"}]}]}
        (root / ".pre-commit-config.yaml").write_text(json.dumps(config), encoding="utf-8")
        source = root / "catalog with spaces.json"
        command = [sys.executable, "-m", "pre_commit", "run", "--all-files"]
        for contents, expected, marker in [
            ('{"Name":1,"name":2}', 0, "Passed"),
            ('{"a":1,"a":2}', 1, "duplicate"),
            ('{"a":', 1, "Expecting value"),
        ]:
            source.write_text(contents, encoding="utf-8")
            run(["git", "add", "--all"], root)
            output = run(command, root, expected)
            assert marker in output, output
    print("Verified pre-commit: clean input, duplicate, invalid JSON and spaced filename")


if __name__ == "__main__":
    main()
