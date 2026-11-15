# Contributing to reposcore

Thanks for helping out! The project is intentionally small: one Python file, no dependencies.

## Setup

```bash
git clone https://github.com/CyberLoop-dev/reposcore.git
cd reposcore
python -m unittest discover -s tests -v
```

## Adding a check

1. Write a function `check_something(root, rels) -> Check` in `reposcore.py`.
2. Add it to the `CHECKS` list.
3. Keep the total of all `max_points` at exactly 100.
4. Add a test in `tests/test_reposcore.py`.

## Guidelines

- Standard library only.
- Never print the value of a detected secret.
- Keep messages short and actionable.
