# AWS CLI

![Build Status](https://github.com/aws/aws-cli/actions/workflows/run-tests.yml/badge.svg)
[Build Status Badge](https://github.com/aws/aws-cli/actions/workflows/run-tests.yml)

This package provides a unified command-line interface (CLI) for interacting with Amazon Web Services (AWS).

## Table of Contents

- [Getting Started](#getting-started)
- [Getting Help](#getting-help)
- [More Resources](#more-resources)

---

## Getting Started

This README is for AWS CLI version 1. If you're looking for information about AWS CLI version 2, please visit the [`v2 branch`](https://github.com/aws/aws-cli/tree/v2).

### Requirements

The AWS CLI supports the following Python versions:

- 3.8.x and above
- 3.9.x and above
- 3.10.x and above
- 3.11.x and above
- 3.12.x and above

**Note:** 

- Support for Python 3.6 ended on May 30, 2022, following Python's official end-of-life for the runtime on December 23, 2021.
- Support for Python 3.7 will end on December 13, 2023, following Python's official end-of-life on June 27, 2023. For more details, see this [blog post](https://aws.amazon.com/blogs/developer/python-support-policy-updates-for-aws-sdks-and-tools/).

*Important:*  
We recommend regularly checking the [Amazon Web Services Security Bulletins](https://aws.amazon.com/security/security-bulletins) for any critical security updates related to AWS CLI.

### Maintenance and Support for CLI Major Versions

AWS CLI version 1 was generally released on 09/02/2013 and is currently in the full support phase. For details on maintenance and support for SDK versions and dependencies, refer to the [AWS SDKs and Tools Shared Configuration and Credentials Reference Guide](https://docs.aws.amazon.com/credref/latest/refdocs/maint-policy.html).

---

## Installation

AWS CLI and its dependencies can be installed using `pip` and `setuptools`. To ensure a smooth installation, make sure you're using:

- `pip`: version 9.0.2 or greater
- `setuptools`: version 36.2.0 or greater

### Installation Steps:

1. **Using `pip` in a virtual environment (recommended):**

   ```bash
   $ python -m pip install awscli
   ```

2. **To install globally:**

   ```bash
   $ sudo python -m pip install awscli
   ```

3. **For user-specific installation:**

   ```bash
   $ python -m pip install --user awscli
   ```

4. **To upgrade the AWS CLI:**

   ```bash
   $ python -m pip install --upgrade awscli
   ```

   This will update the AWS CLI package along with its dependencies.

**Note for macOS Users:**  
If you encounter an issue with the `six` library due to El Capitan's bundled version of `distutils`, use the `--ignore-installed` option:

```bash
$ sudo python -m pip install awscli --ignore-installed six
```

The AWS CLI can also be installed via the [bundled installer](https://docs.aws.amazon.com/cli/latest/userguide/install-linux.html#install-linux-bundled) on Linux and macOS, or through an [MSI installer](https://docs.aws.amazon.com/cli/latest/userguide/install-windows.html#msi-on-windows) on Windows.

For instructions on using the **development version** of AWS CLI, check the [CLI development section](CONTRIBUTING.md#cli-development-version) of the contributing guide.

See the [AWS CLI User Guide](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv1.html) for more installation options.

---

## Configuration

Before using the AWS CLI, you need to configure your AWS credentials. You can configure them in the following ways:

- **Configuration command**
- **Environment variables**
- **Shared credentials file**
- **Config file**
- **IAM Role**

The quickest way to get started is by using the `aws configure` command:

```bash
$ aws configure
AWS Access Key ID: MYACCESSKEY
AWS Secret Access Key: MYSECRETKEY
Default region name [us-west-2]: us-west-2
Default output format [None]: json
```

Alternatively, you can set up your credentials using environment variables:

```bash
$ export AWS_ACCESS_KEY_ID=<access_key>
$ export AWS_SECRET_ACCESS_KEY=<secret_key>
```

Or, by using the shared credentials file, create an INI-formatted file like this:

```ini
[default]
aws_access_key_id=MYACCESSKEY
aws_secret_access_key=MYSECRETKEY

[testing]
aws_access_key_id=MYACCESSKEY
aws_secret_access_key=MYSECRETKEY
```

Place this file in `~/.aws/credentials` (or `%UserProfile%\.aws\credentials` on Windows). If your credentials file is located elsewhere, specify its location with the `AWS_SHARED_CREDENTIALS_FILE` environment variable:

```bash
$ export AWS_SHARED_CREDENTIALS_FILE=/path/to/shared_credentials_file
```

Similarly, you can use a config file:

```ini
[default]
aws_access_key_id=<default access key>
aws_secret_access_key=<default secret key>
# Optional, specify the default region
region=us-west-1

[profile testing]
aws_access_key_id=<testing access key>
aws_secret_access_key=<testing secret key>
region=us-west-2
```

Save this file in `~/.aws/config` (or `%UserProfile%\.aws\config` on Windows). To use a config file located elsewhere, set the `AWS_CONFIG_FILE` environment variable:

```bash
$ export AWS_CONFIG_FILE=/path/to/config_file
```

You can have multiple profiles defined in both the credentials and config files. Use the `--profile` option to specify which profile to use. If no profile is provided, the `default` profile is used.

For profiles other than `default`, prefix the section name with `profile`, e.g., `[profile testing]`.

If you're using an EC2 instance, it's highly recommended to configure [IAM Roles](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html) to automatically assign credentials.

Refer to the [AWS CLI Configuration Variables](http://docs.aws.amazon.com/cli/latest/topic/config-vars.html#cli-aws-help-config-vars) for additional configuration options. For more details, consult the [AWS Tools and SDKs Shared Configuration and Credentials Reference Guide](https://docs.aws.amazon.com/credref/latest/refdocs/overview.html).

---

## Basic Commands

An AWS CLI command follows this structure:

```bash
$ aws <command> <subcommand> [options and parameters]
```

For example, to list all S3 buckets:

```bash
$ aws s3 ls
```

To view help for a command, use:

```bash
$ aws help
$ aws <command> help
$ aws <command> <subcommand> help
```

To check your AWS CLI version:

```bash
$ aws --version
```

To enable debugging output:

```bash
$ aws --debug <command> <subcommand>
```

Refer to the [Using the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-using.html) section in the AWS CLI User Guide for more details.

---

## Command Completion

The AWS CLI includes command completion for Unix-like systems, but it must be manually configured. Learn more in the [AWS CLI Command Completion](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-completion.html) documentation.

---

## Getting Help

For assistance, the best option is to open an issue on [GitHub](https://github.com/aws/aws-cli/issues/new/choose), where you can select from templates for guidance, bug reports, or feature requests.

For community support, visit:

- [Stack Overflow](https://stackoverflow.com/) with the `aws-cli` tag
- [AWS Discussion Forum for CLI](https://forums.aws.amazon.com/forum.jspa?forumID=150)

If you have a support plan with AWS, you can create a support case through the [AWS Support Console](https://console.aws.amazon.com/support/home#/).

Please check for similar [open issues](https://github.com/aws/aws-cli/issues/) before creating a new one.

For AWS service-related issues or limitations, check the [Amazon Web Services Discussion Forums](https://forums.aws.amazon.com/).

---

## More Resources

- [Changelog](https://github.com/aws/aws-cli/blob/develop/CHANGELOG.rst)
- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/index.html)
- [AWS CLI User Guide](https://docs.aws.amazon.com/cli/latest/userguide/)
- [AWS CLI Command Reference](https://docs.aws.amazon.com/cli/latest/reference/)
- [AWS Discussion Forums](https://forums.aws.amazon.com/)
- [AWS Support](https://console.aws.amazon.com/support/home#/)

---

| ![Build Status](https://travis-ci.org/aws/aws-cli.svg?branch=develop) | [Build Status](https://travis-ci.org/aws/aws-cli) |
| --- | --- |
| ![Gitter](https://badges.gitter.im/aws/aws-cli.svg) | [Gitter](https://gitter.im/aws/aws-cli) |
