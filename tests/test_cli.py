import contextlib
import io
import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from locale_tripwire.cli import collect_files, github_annotation, inspect_json, main, workflow_escape


class CollisionTests(unittest.TestCase):
    def test_workflow_command_escaping(self):
        self.assertEqual(workflow_escape("%,:\r\n", property_value=True), "%25%2C%3A%0D%0A")
        self.assertEqual(workflow_escape("%\r\n::error::fake"), "%25%0D%0A::error::fake")

    def test_github_annotation_has_relative_location(self):
        root = Path.cwd()
        finding = {"file": str(root / "a%,b.json"),
                   **inspect_json('{"a":1,"a":2}', ("duplicate",))[0]}
        annotation = github_annotation(finding, root)
        self.assertTrue(annotation.startswith("::error file=a%25%2Cb.json,line=1,col=8::"))
        self.assertIn("first key at 1:2", annotation)

    def test_github_annotation_omits_external_file(self):
        root = Path.cwd() / "child"
        finding = {"file": str(Path.cwd() / "a.json"),
                   **inspect_json('{"a":1,"a":2}', ("duplicate",))[0]}
        annotation = github_annotation(finding, root)
        self.assertTrue(annotation.startswith("::error::"))
        self.assertIn("outside annotation root", annotation)

    def test_github_output_cannot_inject_extra_commands(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "a.json"
            key = "\n::error::pretend%"
            path.write_text('{' + json.dumps(key) + ':1,' + json.dumps(key) + ':2}', encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main([str(path), "--rules", "duplicate", "--severity", "duplicate=warning",
                                       "--format", "github", "--annotation-root", folder]), 0)
            self.assertEqual(len(output.getvalue().splitlines()), 1)
            self.assertTrue(output.getvalue().startswith("::warning file=a.json,line=1,"))
            self.assertIn("%25", output.getvalue())

    def test_github_input_errors_are_annotations(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(["missing.json", "--format", "github"]), 2)
        self.assertTrue(output.getvalue().startswith("::error::"))

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
        self.assertEqual(findings[0]["path"], '$["items"][0]')

    def test_ambiguous_property_name_is_escaped(self):
        findings = inspect_json('{"a.b": {"Name": 1, "name": 2}}')
        self.assertEqual(findings[0]["path"], '$["a.b"]')

    def test_nonstandard_json_constant_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "nan.json"
            path.write_text('{"value": NaN}', encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(path), "--format", "json"]), 2)

    def test_surrogate_key_does_not_crash_json_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "surrogate.json"
            path.write_text('{"\\ud800": 1, "\\ud800": 2}', encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main([str(path), "--format", "json"]), 1)
            self.assertIn("\\ud800", output.getvalue())

    def test_clean_document(self):
        self.assertEqual(inspect_json('{"title": "Hello", "count": 1}'), [])

    def test_selected_rule_ignores_other_collisions(self):
        self.assertEqual(inspect_json('{"Name": 1, "name": 2}', ("duplicate",)), [])
        findings = inspect_json('{"Name": 1, "name": 2}', ("casefold",))
        self.assertEqual([item["rule"] for item in findings], ["casefold"])

    def test_invalid_api_settings(self):
        for rules, severities in [((), {}), (("unknown",), {}), (("nfc",), {"nfc": "quiet"})]:
            with self.subTest(rules=rules, severities=severities), self.assertRaises(ValueError):
                inspect_json('{}', rules, severities)

    def test_positions_and_codepoints(self):
        source = '{\r\n  "café": 1,\r\n  "cafe\\u0301": 2\r\n}'
        finding = inspect_json(source, ("nfc",))[0]
        self.assertEqual(finding["first_position"], {"line": 2, "column": 3})
        self.assertEqual(finding["second_position"], {"line": 3, "column": 3})
        self.assertEqual(finding["transformed"], "café")
        self.assertIn("U+0301 COMBINING ACUTE ACCENT", finding["second_codepoints"])

    def test_escaped_duplicate_and_first_occurrence(self):
        findings = inspect_json('{"a":0,"\\u0061":1,"a":2}', ("duplicate",))
        self.assertEqual(len(findings), 2)
        self.assertEqual(findings[0]["first_position"], {"line": 1, "column": 2})
        self.assertEqual(findings[0]["second_position"], {"line": 1, "column": 8})
        self.assertEqual(findings[1]["first_position"], findings[0]["first_position"])

    def test_parser_skips_key_like_strings_and_handles_all_values(self):
        source = json.dumps({"text": '"Name":1,"name":2', "items": [None, True, False, -1.2e3, {}, []]})
        self.assertEqual(inspect_json(source), [])
        for source in ['null', 'true', '42', '"text"', '[]', ' {} \n']:
            with self.subTest(source=source):
                self.assertEqual(inspect_json(source), [])

    def test_nested_objects_keep_independent_positions(self):
        source = '{"a":{"X":1,"x":2},"b":{"X":3,"x":4}}'
        findings = inspect_json(source, ("casefold",))
        self.assertEqual([item["path"] for item in findings], ['$["a"]', '$["b"]'])
        self.assertNotEqual(findings[0]["first_position"], findings[1]["first_position"])

    def test_root_array_and_empty_keys(self):
        finding = inspect_json('[{}, {"":1,"":2}]', ("duplicate",))[0]
        self.assertEqual(finding["path"], '$[1]')
        self.assertEqual(finding["first_codepoints"], [])
        self.assertEqual(finding["transformed"], '')

    def test_invalid_syntax_never_reaches_position_parser(self):
        for source in ['{"x":1,}', '{"x" 1}', '[1,]', '{"x":1} trailing', '']:
            with self.subTest(source=source), self.assertRaises(json.JSONDecodeError):
                inspect_json(source)

    def test_three_distinct_colliding_keys_keep_first(self):
        findings = inspect_json('{"Name":1,"NAME":2,"name":3}', ("casefold",))
        self.assertEqual([item["first"] for item in findings], ["Name", "Name"])

    def test_character_columns_not_utf8_byte_offsets(self):
        findings = inspect_json('{"é":0,"X":1,"x":2}', ("casefold",))
        self.assertEqual(findings[0]["first_position"], {"line": 1, "column": 8})

    def test_warning_exit_threshold(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "case.json"
            path.write_text('{"X":1,"x":2}', encoding="utf-8")
            args = [str(path), "--rules", "casefold", "--severity", "casefold=warning", "--format", "json"]
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(args), 0)
                self.assertEqual(main(args + ["--fail-on", "warning"]), 1)
            self.assertIn('"severity": "warning"', output.getvalue())

    def test_errors_override_warning_threshold(self):
        with tempfile.TemporaryDirectory() as folder:
            good, bad = Path(folder) / "a.json", Path(folder) / "b.json"
            good.write_text('{"X":1,"x":2}', encoding="utf-8")
            bad.write_text('{', encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(good), str(bad), "--rules", "casefold",
                                       "--severity", "casefold=warning", "--format", "json"]), 2)

    def test_invalid_cli_options_fail_before_reading(self):
        for options in [["--rules", ""], ["--rules", "nfc,typo"], ["--severity", "nfc=quiet"],
                        ["--rules", "duplicate", "--severity", "nfc=warning"]]:
            with self.subTest(options=options), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as exc:
                    main(["unused.json", *options])
                self.assertEqual(exc.exception.code, 2)

    def test_recursive_scan_excludes_and_deduplicates(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ["nested/a.json", "b.json", "nested/skip.json", "generated/c.json",
                         "node_modules/d.json", ".git/e.json", "nested/plain.txt"]:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{}', encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(root), "--exclude", "skip.json", "--exclude", "generated"]), 0)
            files, errors = collect_files([root, root / "b.json"],
                                          ["node_modules", ".git", "skip.json", "generated"], ["*.json"])
            self.assertEqual(errors, [])
            self.assertEqual([path.relative_to(root).as_posix() for path in files], ["b.json", "nested/a.json"])

    def test_include_and_root_relative_exclude(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ["catalog/a.json", "catalog/b.txt", "other/a.json"]:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('{}', encoding="utf-8")
            files, errors = collect_files([root], ["catalog/*.json"], ["*.json", "*.txt"])
            self.assertEqual(errors, [])
            self.assertEqual([p.relative_to(root).as_posix() for p in files], ["catalog/b.txt", "other/a.json"])

    def test_empty_directory_is_not_silent_success(self):
        with tempfile.TemporaryDirectory() as folder, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main([folder, "--format", "json"]), 2)

    def test_walk_errors_are_not_silent_success(self):
        with tempfile.TemporaryDirectory() as folder:
            def failed_walk(root, **kwargs):
                kwargs["onerror"](PermissionError("cannot read directory"))
                return iter([])
            with patch("locale_tripwire.cli.os.walk", side_effect=failed_walk):
                files, errors = collect_files([Path(folder)], [], ["*.json"])
            self.assertEqual(files, [])
            self.assertIn("cannot read directory", errors)

    def test_unresolvable_input_is_reported(self):
        with patch.object(Path, "resolve", side_effect=RuntimeError("symlink loop")):
            files, errors = collect_files([Path("missing.json")], [], ["*.json"])
        self.assertEqual(files, [])
        self.assertIn("symlink loop", errors[0])

    def test_explicit_file_overrides_directory_filters(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.txt"
            path.write_text('{}', encoding="utf-8")
            files, errors = collect_files([path], ["data.txt"], ["*.json"])
            self.assertEqual((files, errors), ([path], []))

    def test_symlinks_are_not_followed_in_directories(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "a.json").write_text('{}', encoding="utf-8")
            try:
                (root / "loop").symlink_to(root, target_is_directory=True)
                (root / "link.json").symlink_to(root / "a.json")
            except (OSError, NotImplementedError):
                self.skipTest("symlinks unavailable for this account")
            files, errors = collect_files([root], [], ["*.json"])
            self.assertEqual((files, errors), ([root / "a.json"], []))

    def test_text_output_is_ascii_safe_and_explains_positions(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ş.json"
            path.write_text('{"\\ud800":1,"\\ud800":2}', encoding="utf-8")
            buffer = io.BytesIO()
            stream = io.TextIOWrapper(buffer, encoding="cp1252")
            with contextlib.redirect_stdout(stream):
                self.assertEqual(main([str(path), "--rules", "duplicate"]), 1)
            stream.flush()
            text = buffer.getvalue().decode("ascii")
            self.assertIn("first key: 1:2", text)
            self.assertIn("U+D800", text)
            self.assertIn("shared transformed key", text)
            stream.detach()

    def test_mixed_input_reports_findings_and_errors(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "a.json").write_text('{"a":1,"a":2}', encoding="utf-8")
            (root / "b.json").write_bytes(b'\xff')
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main([folder, "--format", "json"]), 2)
            report = json.loads(output.getvalue())
            self.assertEqual(len(report["findings"]), 1)
            self.assertEqual(len(report["errors"]), 1)

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
