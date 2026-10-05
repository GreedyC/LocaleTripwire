"""Reject mutable refs or tags that don't match the distribution version.

This release-only script runs on Python 3.14, not inside the installed package.
"""

import os
from pathlib import Path
import re
import subprocess


def validate_tag(tag: str, version: str) -> None:
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+", tag) or tag != f"v{version}":
        raise ValueError("RELEASE_TAG must be vMAJOR.MINOR.PATCH matching pyproject.toml")


def main() -> None:
    import tomllib  # release runner uses Python 3.14; helpers also test on 3.10
    repo = Path(__file__).resolve().parents[1]
    metadata = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    tag = os.environ.get("RELEASE_TAG", "")
    validate_tag(tag, metadata["project"]["version"])
    def revision(ref: str) -> str:
        return subprocess.check_output(["git", "rev-parse", "--verify", ref], cwd=repo,
                                       text=True).strip()
    if revision(f"refs/tags/{tag}^{{commit}}") != revision("HEAD"):
        raise ValueError("checkout must match the immutable version tag")
    print(f"Verified release tag {tag}")


if __name__ == "__main__":
    main()
