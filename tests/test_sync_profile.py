import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("sync_profile", Path(__file__).resolve().parents[1] / "scripts/sync_profile.py")
SYNC = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SYNC)


def readme():
    return "Header\n" + "\n".join(
        f"<!-- {marker}_STATUS:START -->版本待核实<!-- {marker}_STATUS:END -->"
        for marker in SYNC.RELEASES
    ) + "\nFooter\n"


class ProfileSyncTests(unittest.TestCase):
    def test_updates_both_markers_and_preserves_surrounding_copy(self):
        tags = {"GERAIQ": "v0.8", "85MEGA": "v2026.11.09"}
        result = SYNC.update_markers(readme(), tags)
        self.assertTrue(result.startswith("Header\n"))
        self.assertTrue(result.endswith("\nFooter\n"))
        self.assertIn("GitHub Release `v0.8`", result)
        self.assertIn("GitHub Release `v2026.11.09`", result)
        self.assertEqual(SYNC.update_markers(result, tags), result)

    def test_rejects_missing_duplicate_or_reversed_markers(self):
        for value in ("no markers", readme() + readme(), "<!-- GERAIQ_STATUS:END --><!-- GERAIQ_STATUS:START -->"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                SYNC.update_markers(value, {"GERAIQ": "v1"})

    def test_rejects_code_markup_and_multiline_tags(self):
        for tag in ("v1`oops", "<img>", "v1\nattack", "$(command)", "v1" + "a" * 80, None):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                SYNC.update_markers(readme(), {"GERAIQ": tag})

    @patch.object(SYNC.subprocess, "run")
    def test_reads_release_as_json_data(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, json.dumps({"tag_name": "v1.2.3"}), "")
        self.assertEqual(SYNC.latest_tag("jazkng/geraiq"), "v1.2.3")
        self.assertNotIn("shell", run.call_args.kwargs)

    @patch.object(SYNC.subprocess, "run")
    def test_rejects_access_error_and_invalid_response(self, run):
        for code, body in ((1, "private error"), (0, "invalid JSON"), (0, "{}"), (0, '{"tag_name": "v1`"}')):
            run.return_value = subprocess.CompletedProcess([], code, body, "sensitive stderr")
            with self.subTest(code=code, body=body), self.assertRaises(ValueError):
                SYNC.latest_tag("jazkng/geraiq")

    def test_missing_token_skips_api_and_records_truthful_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = Path(directory) / "summary.md"
            with patch.dict(os.environ, {"GH_TOKEN": "", "GITHUB_STEP_SUMMARY": str(summary)}), patch.object(SYNC, "latest_tag") as fetch:
                SYNC.main()
                fetch.assert_not_called()
            self.assertIn("No release version was verified", summary.read_text())

    def test_failed_second_request_preserves_readme(self):
        with patch.dict(os.environ, {"GH_TOKEN": "synthetic-test-value"}), patch.object(SYNC.Path, "read_text", return_value=readme()), patch.object(SYNC.Path, "write_text") as write, patch.object(SYNC, "latest_tag", side_effect=["v1", ValueError("access denied")]):
            with self.assertRaises(ValueError):
                SYNC.main()
            write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
