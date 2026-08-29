"""Tests for skills/ste/scripts/ste_check.py.

Run:  python3 -m unittest discover -s tests
"""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "skills", "ste", "scripts", "ste_check.py")

spec = importlib.util.spec_from_file_location("ste_check", SCRIPT)
ste = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ste)


class Opts:
    procedural = False


def findings(text, procedural=False, terms=frozenset()):
    opts = Opts()
    opts.procedural = procedural
    return ste.check_text(text, opts, None, set(terms))


def rules(text, **kw):
    return [f.rule for f in findings(text, **kw)]


class IngForms(unittest.TestCase):
    def test_ing_noun_in_object_position_is_not_flagged(self):
        self.assertNotIn("1.5", rules("The sibling node has a standing constraint."))

    def test_ing_technical_noun_is_not_flagged(self):
        self.assertNotIn("1.5", rules("The cost of fuzzing is high."))

    def test_ing_after_preposition_is_flagged(self):
        found = findings("Before installing the pump, close the valve.")
        self.assertEqual([f.rule for f in found], ["1.5"])
        self.assertEqual(found[0].severity, "error")
        self.assertIn("installing", found[0].message)

    def test_ing_at_sentence_start_is_flagged(self):
        self.assertIn("1.5", rules("Installing the pump takes one hour."))

    def test_ing_after_preposition_in_project_terms_is_not_flagged(self):
        self.assertNotIn("1.5", rules("Start by sharding the table.", terms={"sharding"}))


class SentenceLength(unittest.TestCase):
    def test_instruction_limit_message_uses_an(self):
        text = "1. " + " ".join(["word"] * 21) + "."
        found = findings(text)
        self.assertEqual([f.rule for f in found], ["4.1"])
        self.assertIn("in an instruction", found[0].message)


class NounClusters(unittest.TestCase):
    def test_four_content_words_are_not_flagged(self):
        self.assertNotIn("2.1", rules("Read every gate doc under review today."))


class Slashes(unittest.TestCase):
    def test_relative_path_is_not_flagged(self):
        self.assertNotIn("8.2", rules("See ../how-to for the steps."))

    def test_uppercase_abbreviation_is_not_flagged(self):
        self.assertNotIn("8.2", rules("The I/O cost is low."))

    def test_unit_is_not_flagged(self):
        self.assertNotIn("8.2", rules("The rate is 40 frames/s at most."))

    def test_and_or_slash_is_flagged(self):
        found = findings("Set the read/write mode.")
        self.assertEqual([f.rule for f in found], ["8.2"])
        self.assertEqual(found[0].severity, "error")


class Severity(unittest.TestCase):
    def test_semicolon_is_an_error(self):
        found = findings("Close the valve; open the door.")
        self.assertEqual([(f.rule, f.severity) for f in found], [("8.6", "error")])

    def test_passive_in_descriptive_text_is_a_warning(self):
        found = findings("The value is configured by the operator.")
        self.assertEqual([(f.rule, f.severity) for f in found], [("3.1", "warning")])

    def test_passive_in_procedural_text_is_an_error(self):
        found = findings("The valve is closed by the operator.", procedural=True)
        self.assertEqual([(f.rule, f.severity) for f in found], [("3.1", "error")])

    def test_passive_in_list_item_is_an_error(self):
        found = findings("1. The valve is closed by the operator.")
        self.assertEqual([(f.rule, f.severity) for f in found], [("3.1", "error")])

    def test_trailing_condition_is_a_warning(self):
        found = findings("Close the valve if the light is on.")
        self.assertEqual([(f.rule, f.severity) for f in found], [("4.4", "warning")])


class Tables(unittest.TestCase):
    def test_table_rows_are_skipped(self):
        text = "| Limit | Where |\n|---|---|\n| Chunking is done here; see writing | ../how-to |\n"
        self.assertEqual(findings(text), [])


class Report(unittest.TestCase):
    def test_one_line_per_sentence_with_all_rules(self):
        text = "Utilize the read/write mode; then stop."
        out = ste.format_report("doc.md", findings(text))
        body = [line for line in out.splitlines() if line.startswith("  ")]
        self.assertEqual(len(body), 1)
        self.assertIn("1.1", body[0])
        self.assertIn("8.2", body[0])
        self.assertIn("8.6", body[0])
        self.assertIn("Utilize the read/write", body[0])

    def test_summary_line_counts_by_severity(self):
        text = "Close the valve; open the door. The value is configured by the operator."
        out = ste.format_report("doc.md", findings(text))
        self.assertIn("1 error, 1 warning", out)

    def test_json_format(self):
        text = "Close the valve; open the door."
        data = json.loads(ste.format_json("doc.md", findings(text)))
        self.assertEqual(data[0]["file"], "doc.md")
        self.assertEqual(data[0]["rule"], "8.6")
        self.assertEqual(data[0]["severity"], "error")
        self.assertEqual(data[0]["line"], 1)


class ExitCode(unittest.TestCase):
    def run_checker(self, text, *args):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as handle:
            handle.write(text)
            path = handle.name
        try:
            proc = subprocess.run(
                [sys.executable, SCRIPT, "--terms", os.devnull, *args, path],
                capture_output=True, text=True,
            )
        finally:
            os.unlink(path)
        return proc

    def test_warnings_alone_exit_zero(self):
        proc = self.run_checker("The value is configured by the operator.\n")
        self.assertEqual(proc.returncode, 0, proc.stdout)
        self.assertIn("0 errors, 1 warning", proc.stdout)

    def test_errors_exit_one(self):
        proc = self.run_checker("Close the valve; open the door.\n")
        self.assertEqual(proc.returncode, 1, proc.stdout)

    def test_fail_on_warning(self):
        proc = self.run_checker("The value is configured by the operator.\n", "--fail-on", "warning")
        self.assertEqual(proc.returncode, 1, proc.stdout)

    def test_json_is_one_flat_list_across_files(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as second:
            second.write("Close the valve; open the door.\n")
        try:
            proc = self.run_checker("The value is configured by the operator.\n", "--format", "json", second.name)
        finally:
            os.unlink(second.name)
        data = json.loads(proc.stdout)
        self.assertEqual(sorted(d["rule"] for d in data), ["3.1", "8.6"])
        self.assertEqual(len({d["file"] for d in data}), 2)

    def test_clean_file_prints_zero_line(self):
        proc = self.run_checker("Close the valve.\n")
        self.assertEqual(proc.returncode, 0)
        self.assertIn("0 errors, 0 warnings", proc.stdout)


if __name__ == "__main__":
    unittest.main()
