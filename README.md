# AWS CLI v1-to-v2 Migration Tool

A CLI tool that lints bash scripts for AWS CLI v1 usage and updates them to avoid breaking 
changes introduced in AWS CLI v2. Not all breaking changes can be detected statically, 
thus not all of them are supported by this tool.

For a full list of the breaking changes introduced with AWS CLI v2, see 
[Breaking changes between AWS CLI version 1 and AWS CLI version 2](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-changes-breaking).

## Installation

Most users should install AWS CLI v1-to-v2 Migration Tool via `pip` in a `virtualenv`:

```shell
$ python3 -m pip install aws-cli-migrate
```

or, if you are not installing in a `virtualenv`, to install globally:

```shell
$ sudo python3 -m pip install aws-cli-migrate
```

or for your user:

```shell
$ python3 -m pip install --user aws-cli-migrate
```

If you have the `aws-cli-migrate` package installed and want to upgrade to the latest version, you can run:

```shell
$ python3 -m pip install --upgrade aws-cli-migrate
```

This will install the `aws-cli-migrate` package as well as all dependencies.

If you want to run `aws-cli-migrate` from source, see the [Installing development versions](#installing-development-versions) section.

## Usage

### Dry-run mode (default)
Display issues without modifying the script:
```bash
migrate-aws-cli --script upload_s3_files.sh
```

### Fix mode
Automatically update the input script:
```bash
migrate-aws-cli --script upload_s3_files.sh --fix
```

### Output mode
Create a new fixed script without modifying the original:
```bash
migrate-aws-cli --script upload_s3_files.sh --output upload_s3_files_v2.sh
```

### Interactive mode
Review and accept/reject each change individually:
```bash
migrate-aws-cli --script upload_s3_files.sh --interactive --output upload_s3_files_v2.sh
```

In interactive mode, you can:
- Press `y` to accept the current change
- Press `n` to skip the current change
- Press `u` to accept all remaining changes
- Press `s` to save and exit
- Press `q` to quit without saving

## Development

### Installing development versions

If you are interested in using the latest released version of the AWS CLI v1-to-v2 Migration Tool, please see the [Installation](#installation) section. 
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
