# AWS CLI v1-to-v2 Upgrade Linter

A CLI tool that lints bash scripts for AWS CLI v1 usage and updates them to avoid breaking 
changes introduced in AWS CLI v2. Not all breaking changes can be detected statically, 
thus not all of them are supported by this tool.

For a full list of the breaking changes introduced with AWS CLI v2, see 
[Breaking changes between AWS CLI version 1 and AWS CLI version 2](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-changes-breaking).

## Installation

Most users should install AWS CLI Linter via `pip` in a `virtualenv`:

```shell
$ python3 -m pip install awsclilinter
```

or, if you are not installing in a `virtualenv`, to install globally:

```shell
$ sudo python3 -m pip install awsclilinter
```

or for your user:

```shell
$ python3 -m pip install --user awsclilinter
```

If you have the `awsclilinter` package installed and want to upgrade to the latest version, you can run:

```shell
$ python3 -m pip install --upgrade awscli
```

This will install the `awsclilinter` package as well as all dependencies.

If you want to run `awsclilinter` from source, see the [Installing development versions](#installing-development-versions) section.

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

### Installing development versions

If you are interested in using the latest released version of the AWS CLI Linter, please see the [Installation](#installation) section. 
This section is for anyone who wants to install the development version of the AWS CLI Linter. You might need to do this if:

* You are developing a feature for the AWS CLI Linter and plan on submitting a Pull Request.
* You want to test the latest changes of the AWS CLI Linter before they make it into an official release.

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

### Running tests
```bash
make test
```

### Code formatting
```bash
make format
```
