# Contributing

Thanks for your interest in Sovereign RAG. This project is a typed, hexagonal
reference architecture — contributions should preserve that discipline.

## Development setup

```bash
make install          # uv sync --extra dev
cp .env.example .env
make demo             # sanity-check the offline pipeline
```

Everything runs offline by default (fake/in-memory providers) — no keys or Docker needed.

## Quality gates (must be green before a PR)

```bash
make lint             # ruff (line-length 100, ANN/B/SIM/RUF rules)
make typecheck        # mypy strict
make test             # pytest (unit + integration, coverage)
make precommit        # all hooks
```

CI (`quality` + `helm` jobs) runs the same gates on every PR. For Helm changes,
also run `make helm-lint` and `make helm-template` (requires `helm`).

## Branching & PR flow

- Branch off `develop` (e.g. `feature/<topic>`); never commit straight to `main`.
- Open the PR against `develop`. Releases are promoted `develop → main` and tagged `vX.Y.Z`.
- Keep PRs focused; update tests and docs in the same PR.
- Commit messages: imperative subject, a body explaining the *why*. Co-author trailers welcome.

## Coding conventions

- **Strict typing** everywhere — annotate all params and returns; no bare `Any`/`dict`/`list`;
  no `# type: ignore` without a documented reason.
- **No comments** in code (self-documenting); use the project logger, not `print`.
- One function = one responsibility (~30 lines max). No hardcoded secrets/IPs/paths.
- Config comes from `pydantic-settings` (`SRAG_` prefix), never inline constants.

## Adding a provider (the pattern)

The hexagon keeps providers swappable. To add one:

1. Define/extend a `Protocol` in `ports/` (no SDK imports there).
2. Implement an adapter in `adapters/` — **import heavy SDKs lazily** inside the adapter so the
   package stays importable without optional deps. Add a fake to `adapters/fakes.py` for tests.
3. Add the provider enum + settings in `config.py`, and branch on it in the relevant `build_*`
   factory in `container.py`.
4. Declare any new dependency as an **optional extra** in `pyproject.toml` (+ mypy override if it
   ships no stubs).
5. Add unit + integration tests using the fakes; never hit live services in tests.

## Tests

- Mirror the `tests/unit` + `tests/integration` split; name tests `test_<function>_<case>`.
- At minimum: one nominal case + one error/edge case. Mock external services.
- Preserve **hard multi-tenant isolation** — add a cross-tenant denial test when touching
  retrieval, ingestion, fine-tuning or the PII vault.

See [`CLAUDE.md`](CLAUDE.md) and [`docs/architecture.md`](docs/architecture.md) for the big picture.
