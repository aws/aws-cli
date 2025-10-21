# AWS CLI Linter

A CLI tool that lints bash scripts for AWS CLI v1 usage and updates them to avoid breaking 
changes introduced in AWS CLI v2. Not all breaking changes can be detected statically, 
thus not all of them are supported by this tool.

For a full list of the breaking changes introduced with AWS CLI v2, see 
[Breaking changes between AWS CLI version 1 and AWS CLI version 2](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-changes-breaking).

## Installation

Run `make setup` to set up a virtual environment with the linter installed. Alternatively, 
you can follow the steps below.

1. Create a virtual environment:
```bash
python3.12 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev-lock.txt
```

3. Install the package in development mode:
```bash
pip install -e .
```

## Usage

### Dry-run mode (default)
Display issues without modifying the script:
```bash
upgrade-aws-cli --script upload_s3_files.sh
```

### Fix mode
Automatically update the input script:
```bash
upgrade-aws-cli --script upload_s3_files.sh --fix
```

### Output mode
Create a new fixed script without modifying the original:
```bash
upgrade-aws-cli --script upload_s3_files.sh --output upload_s3_files_v2.sh
```

### Interactive mode
Review and accept/reject each change individually:
```bash
upgrade-aws-cli --script upload_s3_files.sh --interactive --output upload_s3_files_v2.sh
```

In interactive mode, you can:
- Press `y` to accept the current change
- Press `n` to skip the current change
- Press `u` to accept all remaining changes
- Press `q` to cancel and quit

## Development

### Running tests
```bash
make test
```

### Code formatting
```bash
make format
```
