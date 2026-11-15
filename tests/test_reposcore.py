import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import reposcore  # noqa: E402

GOOD_README = "# Title\n\n## Install\n\n## Usage\n\n```\nrun it\n```\n" + "text " * 120


def make_repo(files):
    tmp = tempfile.TemporaryDirectory()
    for rel, content in files.items():
        path = Path(tmp.name, rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return tmp


FULL = {
    "README.md": GOOD_README,
    "LICENSE": "MIT",
    "tests/test_a.py": "pass\n",
    ".github/workflows/ci.yml": "name: ci\n",
    ".gitignore": "__pycache__/\n",
    "CONTRIBUTING.md": "welcome\n",
    "pyproject.toml": "[project]\nname='x'\n",
}


class ScoreTests(unittest.TestCase):
    def test_empty_repo_only_earns_secret_points(self):
        with make_repo({}) as d:
            self.assertEqual(reposcore.scan(Path(d))["score"], 20)

    def test_full_repo_scores_100(self):
        with make_repo(FULL) as d:
            result = reposcore.scan(Path(d))
        self.assertEqual(result["score"], 100)
        self.assertEqual(result["grade"], "A")

    def test_thin_readme_gets_partial_credit(self):
        with make_repo({"README.md": "# Hi\n"}) as d:
            checks = {c["name"]: c for c in reposcore.scan(Path(d))["checks"]}
        self.assertEqual(checks["README present"]["points"], 10)
        self.assertEqual(checks["README quality"]["points"], 0)

    def test_grade_boundaries(self):
        self.assertEqual([reposcore.grade_for(s) for s in (95, 85, 75, 65, 10)], list("ABCDF"))


class SecretTests(unittest.TestCase):
    def test_detects_key_without_printing_it(self):
        key = "AKIA" + "A" * 16
        with make_repo({"config.py": f'KEY = "{key}"\n'}) as d:
            checks = {c["name"]: c for c in reposcore.scan(Path(d))["checks"]}
        secrets = checks["No leaked secrets"]
        self.assertEqual(secrets["points"], 10)
        self.assertIn("config.py:1", secrets["detail"])
        self.assertNotIn(key, secrets["detail"])

    def test_inline_ignore_marker(self):
        key = "AKIA" + "B" * 16
        with make_repo({"a.py": f'KEY = "{key}"  # reposcore:ignore\n'}) as d:
            self.assertEqual(reposcore.find_secrets(Path(d), ["a.py"]), [])

    def test_skips_vendor_folders(self):
        key = "ghp_" + "c" * 36
        with make_repo({"node_modules/x/index.js": f"t='{key}'\n"}) as d:
            self.assertEqual(reposcore.scan(Path(d))["score"], 20)

    def test_secret_penalty_has_floor(self):
        files = {f"f{i}.txt": "AKIA" + "D" * 16 for i in range(5)}
        with make_repo(files) as d:
            checks = {c["name"]: c for c in reposcore.scan(Path(d))["checks"]}
        self.assertEqual(checks["No leaked secrets"]["points"], 0)


class OutputTests(unittest.TestCase):
    def test_badge_mentions_score_and_color(self):
        svg = reposcore.badge_svg(95)
        self.assertIn("95/100", svg)
        self.assertIn("#4c1", svg)
        self.assertIn("#e05d44", reposcore.badge_svg(10))

    def run_main(self, args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = reposcore.main(args)
        return code, buf.getvalue()

    def test_json_output_and_badge_file(self):
        with make_repo(FULL) as d:
            out = Path(d, "badge.svg")
            code, text = self.run_main([d, "--json", "--badge", str(out)])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(text)["score"], 100)
            self.assertTrue(out.read_text().startswith("<svg"))

    def test_min_score_sets_exit_code(self):
        with make_repo({}) as d:
            code, _ = self.run_main([d, "--min-score", "50"])
        self.assertEqual(code, 1)

    def test_bad_path_returns_2(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(reposcore.main(["/definitely/not/here"]), 2)


if __name__ == "__main__":
    unittest.main()
