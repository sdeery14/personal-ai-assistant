# Copilot Instructions (Repository)

## Python dependency management (IMPORTANT)

- This repo uses `uv` for dependency management.
- Do NOT suggest `pip install ...` or `python -m pip ...` as the default.
- Assume dependencies are declared in `pyproject.toml` and a lockfile is used.

### Preferred commands

- Install/sync dependencies: `uv sync`
- Add a dependency: `uv add <package>`
- Add a dev dependency: `uv add --dev <package>`
- Run commands in the project env: `uv run <command>`
- Run tests: `uv run pytest` (or the repo’s test runner)

### Behavior

- When giving setup instructions, provide the `uv` “golden path” first.
- If you mention `pip`, label it explicitly as an exception and explain why.

## General

- Prefer cross-platform commands (Windows/macOS/Linux).
- Keep instructions reproducible and minimal.
