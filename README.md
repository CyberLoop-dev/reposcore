<p align="center">
  <img src="assets/banner.svg" alt="reposcore banner" width="100%">
</p>

<p align="center">
  <a href="https://github.com/CyberLoop-dev/reposcore/actions/workflows/ci.yml"><img src="https://github.com/CyberLoop-dev/reposcore/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <img src="https://img.shields.io/badge/python-3.9%2B-3776ab?logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/dependencies-zero-3fb950" alt="Zero dependencies">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT license"></a>
</p>

**reposcore** looks at a repository and gives it a health score from **0 to 100**. It checks the things that make a project feel trustworthy, prints a clear report, and can write an SVG badge for your README. Pure Python, zero dependencies, one file.

## Quick start

```bash
git clone https://github.com/CyberLoop-dev/reposcore.git
cd reposcore
python reposcore.py /path/to/your/repo
```

Or install the command:

```bash
pip install .
reposcore .
```

Example output:

```text
reposcore 0.1.0  -  /home/me/my-project

  [x] README present         10/10  found
  [~] README quality          7/10  no code block
  [x] License                10/10  found
  [ ] Tests                   0/15  no test files found
  [x] CI configured          15/15  e.g. .github/workflows/ci.yml
  [x] .gitignore              5/5   found
  [ ] Contributing or docs    0/5   no CONTRIBUTING, CHANGELOG or docs/
  [x] Dependency manifest    10/10  found pyproject.toml
  [x] No leaked secrets      20/20  none found

Score: 77/100  (grade C)
```

## What is checked

| Check | Points | What it looks for |
|---|---:|---|
| README present | 10 | A README at the repo root |
| README quality | 10 | 500+ characters, 3+ headings, at least one code block |
| License | 10 | `LICENSE`, `COPYING` or similar |
| Tests | 15 | A `tests/` folder or `test_*.py`, `*.test.js`, `*_test.go` files |
| CI configured | 15 | GitHub Actions, GitLab CI, CircleCI or Azure Pipelines |
| `.gitignore` | 5 | Present at the repo root |
| Contributing or docs | 5 | `CONTRIBUTING`, `CHANGELOG` or a `docs/` folder |
| Dependency manifest | 10 | `pyproject.toml`, `package.json`, `go.mod` and friends |
| No leaked secrets | 20 | Cloud keys, tokens and private keys (-10 per finding) |

Grades: **A** 90+, **B** 80+, **C** 70+, **D** 60+, **F** below.

Secret findings show the file, line and kind only. The secret value is never printed. Add `reposcore:ignore` to a line to skip it.

## Options

| Flag | Description |
|---|---|
| `--json` | Machine-readable output |
| `--badge FILE` | Write an SVG badge, for example `badge.svg` |
| `--min-score N` | Exit with code 1 when the score is below N (great for CI) |
| `--version` | Print the version |

## Use it in CI

```yaml
- name: Repo health
  run: |
    curl -fsSL https://raw.githubusercontent.com/CyberLoop-dev/reposcore/main/reposcore.py -o reposcore.py
    python reposcore.py . --min-score 80
```

## Add a badge

```bash
reposcore . --badge assets/score.svg
```

Then reference it from your README:

```markdown
![repo score](assets/score.svg)
```

## Roadmap

- Outdated dependency detection
- Configurable weights via `reposcore.toml`
- Companion tools: [`readmeforge`](https://github.com/CyberLoop-dev/readmeforge) (README generator) and [`devboard`](https://github.com/CyberLoop-dev/devboard) (dashboard)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Adding a new check takes about ten lines.

## License

[MIT](LICENSE)
