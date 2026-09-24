import json
import tempfile
import unittest
from pathlib import Path

from locale_tripwire.cli import inspect_json, main


class CollisionTests(unittest.TestCase):
    def test_exact_duplicate(self):
        self.assertIn("duplicate", [x["rule"] for x in inspect_json('{"name": 1, "name": 2}')])

    def test_unicode_normalization(self):
        rules = [x["rule"] for x in inspect_json('{"café": 1, "café": 2}')]
        self.assertIn("nfc", rules)

    def test_turkish_case(self):
        rules = [x["rule"] for x in inspect_json('{"ISIK": 1, "ısık": 2}')]
        self.assertIn("tr-lower", rules)

    def test_decomposed_dotted_i(self):
        rules = [x["rule"] for x in inspect_json('{"İ": 1, "i": 2}')]
        self.assertIn("tr-lower", rules)

    def test_nested_location(self):
        findings = inspect_json('{"items": [{"Name": 1, "name": 2}]}')
        self.assertEqual(findings[0]["path"], "$.items[0]")

    def test_clean_document(self):
        self.assertEqual(inspect_json('{"title": "Hello", "count": 1}'), [])

    def test_marker_like_user_key(self):
        self.assertEqual(inspect_json('{"__tripwire_pairs__": {"safe": true}}'), [])

    def test_invalid_json_exit_code(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "broken.json"
            path.write_text('{"bad":', encoding="utf-8")
            self.assertEqual(main([str(path), "--format", "json"]), 2)

    def test_cli_exit_code(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sample.json"
            path.write_text(json.dumps({"Name": 1, "name": 2}), encoding="utf-8")
            self.assertEqual(main([str(path), "--format", "json"]), 1)


if __name__ == "__main__":
    unittest.main()
