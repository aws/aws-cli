# Contributing to AWS CLI v1-to-v2 Migration Tool

Contribution guidelines for the AWS CLI v1-to-v2 Migration Tool.

## Development Setup

### Installing development versions

If you are interested in using the latest released version of the AWS CLI v1-to-v2 Migration Tool, please see the [Installation](https://github.com/aws/aws-cli/blob/v1v2-migration-tool/README.md#installation) section in the README. 
This section is for anyone who wants to install the development version of the AWS CLI v1-to-v2 Migration Tool. You might need to do this if:

* You are developing a feature for the AWS CLI v1-to-v2 Migration Tool and plan on submitting a Pull Request.
* You want to test the latest changes of the AWS CLI v1-to-v2 Migration Tool before they make it into an official release.

Install [uv](https://docs.astral.sh/uv/) if you haven't already, then set up the development environment:

```bash
uv sync --extra dev
```

This will create a virtual environment, install all dependencies, and install the package in development mode.

Activate the virtual environment:
```bash
source .venv/bin/activate
```

### Running the CLI
```bash
migrate-aws-cli --script <script.sh>
```

### Running tests
```bash
uv run pytest tests/ -v
```

### Code formatting
```bash
uv run ruff format aws_cli_migrate tests
uv run ruff check --select I --fix aws_cli_migrate tests
```

### Code linting
```bash
uv run ruff format --check aws_cli_migrate tests
uv run ruff check aws_cli_migrate tests
```

### Clean local workspace
```bash
rm -rf .venv build dist *.egg-info
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```

## Submitting Changes

When you're ready to submit your changes:

1. Ensure all tests pass
2. Ensure code formatting and linting checks pass
3. Submit a Pull Request with a clear description of your changes

## Getting Help

The best way to interact with our team is through GitHub. You can [open an issue](https://github.com/aws/aws-cli/issues/new/choose) and choose the templates for the AWS CLI v1-to-v2 Migration Tool.
