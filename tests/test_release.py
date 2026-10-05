import runpy
from pathlib import Path
import unittest


validate_tag = runpy.run_path(str(Path(__file__).resolve().parents[1] / "scripts" / "verify_release.py"))["validate_tag"]


class ReleaseTagTests(unittest.TestCase):
    def test_matching_stable_version(self):
        validate_tag("v0.1.0", "0.1.0")

    def test_version_mismatch(self):
        with self.assertRaises(ValueError):
            validate_tag("v0.2.0", "0.1.0")

    def test_branch_and_invalid_tag_are_rejected(self):
        for tag in ["main", "", "0.1.0", "v0.1.0/branch", "v0.1.0\n", "v0.1.0rc1"]:
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                validate_tag(tag, "0.1.0")
