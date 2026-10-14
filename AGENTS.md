# AGENTS.md

## Role

This repository contains the AWS Command Line Interface (AWS CLI). Make small,
well-tested changes that match the existing patterns in the surrounding code.
This codebase includes vendored copies of `botocore` and `s3transfer`; treat
those areas with extra care.

## Scope and Precedence

This root `AGENTS.md` applies to the whole repository. Follow the closest
nested `AGENTS.md` if one is added later. Direct user instructions take
precedence.

## Commands

Run commands from the repository root unless noted otherwise.

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev-lock.txt
python -m pip install -e .
```

On Windows, activate the environment with `.venv\Scripts\activate`.

For the same build/install path used by CI:

```bash
python scripts/ci/install
```

### Test

```bash
# Unit and functional tests
python scripts/ci/run-tests

# Unit tests only
python scripts/ci/run-tests unit/

# Functional tests only
python scripts/ci/run-tests functional/

# Single test file
pytest tests/unit/test_clidriver.py

# Single test or test class
pytest tests/unit/test_clidriver.py -k test_name

# Tox matrix, when a full compatibility check is needed
tox
```

`scripts/ci/run-tests` changes into the `tests/` directory before invoking
pytest and removes the repository root from `PYTHONPATH` by default so tests
exercise the installed package.

### Lint and Format

Run pre-commit on staged changes before committing them.

```bash
pre-commit
```

Ruff configuration lives in [pyproject.toml](pyproject.toml). Pre-commit also
runs YAML checks, end-of-file fixes, and trailing whitespace checks.

## Boundaries

Always:

- Preserve Python 3.9+ compatibility.
- Keep code cross-platform across Linux, macOS, and Windows.
- Prefer pytest-style tests and dependency injection over monkeypatching.
- Match surrounding style before introducing new abstractions.
- Run the narrowest relevant tests for the files you change.

Ask first:

- Adding runtime dependencies or changing dependency bounds.
- Large rewrites, broad formatting churn, or public behavior changes not
  directly requested.
- Changes to release, installer, CI, or packaging behavior unless the task is
  explicitly about those areas.

Never:

- Edit `awscli/botocore/data` service model files directly. These are generated
  by the internal build system.
- Treat vendored `awscli/botocore` or `awscli/s3transfer` as ordinary local
  code for broad refactors. Fixes usually originate upstream and are copied
  here.
- Commit secrets, credentials, account IDs, or generated local artifacts.
- Revert user changes in a dirty worktree unless explicitly instructed.

## Where Things Live

- `awscli/`: main source package.
- `awscli/customizations/`: custom high-level CLI commands such as `s3`,
  `configure`, `cloudformation`, `ecs`, `eks`, `sso`, and `login`.
- `awscli/botocore/`, `awscli/s3transfer/`: vendored forks.
- `awscli/botocore/data/`: generated service models.
- `tests/`: unit, functional, and integration tests.
- `scripts/ci/`: install and test entry points.

## Testing Patterns

Use helpers in [awscli/testutils.py](awscli/testutils.py) for functional tests:

- `BaseAWSCommandParamsTest` patches `Endpoint.make_request` and captures
  request params. Example: `self.assert_params_for_cmd("aws s3api list-buckets", {})`.
- `BaseAWSHelpOutputTest` captures rendered help output. Example:
  `self.assert_contains("text")`.
- `BaseCLIDriverTest` creates a full CLI driver with mocked environment
  variables.

Place tests near the behavior being changed:

- Use `tests/unit/` for isolated behavior and small command logic.
- Use `tests/functional/` when the CLI driver, argument parsing, events, or
  request serialization are part of the behavior.
- Avoid `tests/integration/` unless explicitly requested or required for a real
  AWS service interaction.

## Code Style

- Use Ruff and pre-commit as the source of truth for formatting and linting.
- Follow surrounding code patterns for names, structure, and quote style.
- Prefer existing helpers, event hooks, and customization patterns over new
  framework code.

## Git Workflow

- PRs should target the `v2` branch.
- Keep changes focused on the requested behavior.
- Do not include unrelated generated files, profiling outputs, virtualenvs, or
  local editor files.
- Commit messages use imperative mood, a 50-character summary, and no trailing
  punctuation.

## Issues and PRs

Follow the [AWS CLI Contribution Guide](https://aws.github.io/aws-cli/index.html)
and [CONTRIBUTING.rst](CONTRIBUTING.rst) for the full contribution process.
Before proposing or opening a PR, search existing
[issues](https://github.com/aws/aws-cli/issues) and
[pull requests](https://github.com/aws/aws-cli/pulls) to avoid duplicate work.

- For significant new features, open or find an issue for discussion before
  implementation.
- Use the `contribution-ready` label to identify issues where community PRs may
  be submitted.
- When creating issues, choose the matching GitHub issue template: `bug`,
  `feature-request`, `documentation`, or `source-distribution`. These templates
  apply the corresponding labels plus `needs-triage`.
- AI-sourced issues or PRs must be reviewed by a human before submission and
  include a statement like `generated by AI tools, and reviewed by <person>`.
