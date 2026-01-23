# AWS CLI v1-to-v2 Migration Tool

A command-line tool that lints bash scripts for AWS CLI v1 usage and updates them to avoid breaking 
changes introduced in AWS CLI v2. Not all breaking changes can be detected statically, 
thus not all of them are supported by this tool.

For a full list of the breaking changes introduced with AWS CLI v2, see 
[Breaking changes between AWS CLI version 1 and AWS CLI version 2](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-changes-breaking).

Jump to:

* [Installation](#installation)
* [Usage](#usage)
* [Supported Breaking Changes](#supported-breaking-changes)
* [Backwards Compatibility Policy](#backwards-compatibility-policy)
* [Contributing](#contributing)
* [Getting Help](#getting-help)

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

## Usage

### Dry-run mode (default)
Display issues without modifying the script:
```bash
migrate-aws-cli --script upload_s3_files.sh
```


### Auto-fix mode

Automatically update the input script:

```bash
migrate-aws-cli --script upload_s3_files.sh --fix
```

Optionally, supply an output path to write the updated script, rather than updating the 
input bash script:
```bash
migrate-aws-cli --script upload_s3_files.sh --output upload_s3_files_v2.sh --fix
```

### Interactive mode

Review and accept/reject each change individually:
```bash
migrate-aws-cli --script upload_s3_files.sh --interactive --output upload_s3_files_v2.sh
```

In interactive mode, you can:
- Press `y` to accept the current change
- Press `n` to skip the current change
- Press `a` to accept all findings with the current type
- Press `r` to reject all findings with the current type
- Press `u` to accept all remaining changes
- Press `s` to save and exit
- Press `q` to quit without saving

## Supported Breaking Changes

The AWS CLI v1-to-v2 Migration Tool lints bash scripts for usage 
of AWS CLI v1 commands that are likely to face breaking changes after upgrading to AWS CLI v2. 
Additionally, the migration tool can automatically modify bash scripts to prevent breakage caused 
by breaking changes that would be caused by upgrading to AWS CLI v2.

Using the migration tool does not guarantee that all breaking changes will be fully prevented. We recommend 
that users upgrading from AWS CLI v1 to AWS CLI v2 read 
[Breaking changes between AWS CLI version 1 and AWS CLI version 2](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-changes-breaking) 
in [New features and changes in the AWS CLI version 2](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html).

The table below describes which breaking changes the migration tool can detect or automatically 
fix.

| Breaking Change | Detection | Auto-fix |
|----------------|-----------|----------|
| [Environment variable added to set text file encoding](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-encodingenvvar) | ❌ No      | ❌ No     |
| [Binary parameters are passed as base64-encoded strings by default](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-binaryparam) | ✅ Yes     | ✅ Yes    |
| [Improved Amazon S3 handling of file properties and tags for multipart copies](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-s3-copy-metadata) | ✅ Yes         | ✅ Yes        |
| [No automatic retrieval of http:// or https:// URLs for parameters](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-paramfile) | ❌ No         | ❌ No        |
| [Pager used for all output by default](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-output-pager) | ✅ Yes         | ✅ Yes        |
| [Timestamp output values are standardized to ISO 8601 format](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-timestamp) | ❌ No         | ❌ No        |
| [Improved handling of CloudFormation deployments that result in no changes](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-cfn) | ✅ Yes         | ✅ Yes        |
| [Changed default behavior for Regional Amazon S3 endpoint for us-east-1 Region](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-s3-regional-endpoint) | ❌ No         | ❌ No        |
| [Changed default behavior for Regional AWS STS endpoints](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-sts-regional-endpoint) | ❌ No         | ❌ No        |
| [ecr get-login removed and replaced with ecr get-login-password](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-ecr-get-login) | ✅ Yes         | ❌ No        |
| [AWS CLI version 2 support for plugins is changing](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-profile-plugins) | ❌ No         | ❌ No        |
| [Hidden alias support removed](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-aliases) | ✅ Yes         | ✅ Yes        |
| [The api_versions configuration file setting is not supported](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-api-versions) | ❌ No         | ❌ No        |
| [AWS CLI version 2 uses only Signature v4 to authenticate Amazon S3 requests](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-sigv4) | ❌ No         | ❌ No        |
| [AWS CLI version 2 is more consistent with paging parameters](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-skeleton-paging) | ✅ Yes         | ❌ No        |
| [AWS CLI version 2 provides more consistent return codes across all commands](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration-changes.html#cliv2-migration-return-codes) | ❌ No         | ❌ No        |

## Backwards Compatibility Policy

The AWS CLI v1-to-v2 Migration Tool does not guarantee backwards compatibility. In particular, 
this tool may face breaking changes in any future versions.

See [CHANGELOG.md](https://github.com/aws/aws-cli/blob/v1v2-migration-tool/CHANGELOG.md) for details on the changes introduced in each update of the AWS CLI v1-to-v2 
Migration Tool.

## Contributing

If you'd like to contribute to the project, please see our [Contributing Guide](https://github.com/aws/aws-cli/blob/v1v2-migration-tool/CONTRIBUTING.md) for development setup instructions and guidelines.

## Getting Help

The best way to interact with our team is through GitHub. You can [open an issue](https://github.com/aws/aws-cli/issues/new?template=migration-tool.yml) and choose the templates for the AWS CLI v1-to-v2 Migration Tool.

If you have a support plan with AWS Support, you can also create a new support case.

Please check for open similar issues before opening another one.