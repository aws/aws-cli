# aws-cli

[![Build Status](https://travis-ci.org/aws/aws-cli.svg?branch=v2)](https://travis-ci.org/aws/aws-cli)

[![Gitter](https://badges.gitter.im/aws/aws-cli.svg)](https://gitter.im/aws/aws-cli)

This package provides a unified command line interface to Amazon Web Services.

Jump to:

- [Getting Started](#getting-started)
- [Getting Help](#getting-help)
- [More Resources](#more-resources)

## Getting Started

This README is for the AWS CLI version 2. This version does include some "breaking" changes from version 1 that might require you to change your scripts so that they continue to operate as you expect. For a list of new features and breaking changes in version 2, see [Breaking changes – Migrating from AWS CLI version 1 to version 2](https://docs.aws.amazon.com/cli/latest/userguide/cliv2-migration.html).

If you are looking for information about the AWS CLI version 1, please visit the [develop branch](https://github.com/aws/aws-cli/tree/develop).

### Installation

Please see the [installation](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) section of the AWS CLI User Guide for more information.

### Configuration

Before using the AWS CLI, you need to configure your AWS credentials. You can do this in several ways:

- Configuration command
- Environment variables
- Shared credentials file
- Config file
- IAM Role

The quickest way to get started is to run the `aws configure` command:

    $ aws configure
    AWS Access Key ID: MYACCESSKEY
    AWS Secret Access Key: MYSECRETKEY
    Default region name [us-west-2]: us-west-2
    Default output format [None]: json

To use environment variables, do the following:

    $ export AWS_ACCESS_KEY_ID=<access_key>
    $ export AWS_SECRET_ACCESS_KEY=<secret_key>

To use the shared credentials file, create an INI formatted file like this:

    [default]
    aws_access_key_id=MYACCESSKEY
    aws_secret_access_key=MYSECRETKEY

    [testing]
    aws_access_key_id=MYACCESKEY
    aws_secret_access_key=MYSECRETKEY

and place it in `~/.aws/credentials` (or in `%UserProfile%\.aws/credentials` on Windows). If you wish to place the shared credentials file in a different location than the one specified above, you need to tell aws-cli where to find it. Do this by setting the appropriate environment variable:

    $ export AWS_SHARED_CREDENTIALS_FILE=/path/to/shared_credentials_file

To use a config file, create an INI formatted file like this:

    [default]
    aws_access_key_id=<default access key>
    aws_secret_access_key=<default secret key>
    # Optional, to define default region for this profile.
    region=us-west-1

    [profile testing]
    aws_access_key_id=<testing access key>
    aws_secret_access_key=<testing secret key>
    region=us-west-2

and place it in `~/.aws/config` (or in `%UserProfile%\.aws\config` on Windows). If you wish to place the config file in a different location than the one specified above, you need to tell the AWS CLI where to find it. Do this by setting the appropriate environment variable:

    $ export AWS_CONFIG_FILE=/path/to/config_file

As you can see, you can have multiple `profiles` defined in both the shared credentials file and the configuration file. You can then specify which profile to use by using the `--profile` option. If no profile is specified the `default` profile is used.

In the config file, except for the default profile, you **must** prefix each config section of a profile group with `profile`. For example, if you have a profile named \"testing\" the section header would be `[profile testing]`.

The final option for credentials is highly recommended if you are using the AWS CLI on an EC2 instance. [IAM Roles](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/iam-roles-for-amazon-ec2.html) are a great way to have credentials installed automatically on your instance. If you are using IAM Roles, the AWS CLI will find and use them automatically.

In addition to credentials, a number of other variables can be configured either with environment variables, configuration file entries, or both. See the [AWS Tools and SDKs Shared Configuration and Credentials Reference Guide](https://docs.aws.amazon.com/credref/latest/refdocs/overview.html) for more information.

For more information about configuration options, please refer to the [AWS
CLI Configuration Variables topic](http://docs.aws.amazon.com/cli/latest/topic/config-vars.html#cli-aws-help-config-vars). You can access this topic from the AWS CLI as well by running `aws help config-vars`.

### Basic Commands

An AWS CLI command has the following structure:

    $ aws <command> <subcommand> [options and parameters]

For example, to list S3 buckets, the command would be:

    $ aws s3 ls

To view help documentation, use one of the following:

    $ aws help
    $ aws <command> help
    $ aws <command> <subcommand> help

To get the version of the AWS CLI:

    $ aws --version

To turn on debugging output:

    $ aws --debug <command> <subcommand>

You can read more information on the [Using the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-using.html) chapter of the AWS CLI User Guide.

### Command Completion

The AWS CLI includes a command completion feature for Unix-like systems. This feature is not automatically installed so you need to configure it manually. To learn more, read the [AWS CLI Command completion topic](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-completion.html).

## Getting Help

The best way to interact with our team is through GitHub. You can [open an issue](https://github.com/aws/aws-cli/issues/new/choose) and choose from one of our templates for guidance, bug reports, or feature requests.

You may find help from the community on [Stack Overflow](https://stackoverflow.com/) with the tag [aws-cli](https://stackoverflow.com/questions/tagged/aws-cli) or on the [AWS Discussion Forum for CLI](https://forums.aws.amazon.com/forum.jspa?forumID=150). If you have a support plan with [AWS Premium Support](https://aws.amazon.com/premiumsupport), you can also create a new support case.

Please check for open similar [issues](https://github.com/aws/aws-cli/issues/) before opening another one.

The AWS CLI implements AWS service APIs. For general issues regarding the services or their limitations, you may find the [Amazon Web Services Discussion Forums](https://forums.aws.amazon.com/) helpful.

## More Resources

- [Changelog](https://github.com/aws/aws-cli/blob/v2/CHANGELOG.rst)
- [AWS CLI Documentation](https://docs.aws.amazon.com/cli/index.html)
- [AWS CLI User Guide](https://docs.aws.amazon.com/cli/latest/userguide/)
- [AWS CLI Command Reference](https://docs.aws.amazon.com/cli/latest/reference/)
- [Amazon Web Services Discussion Forums](https://forums.aws.amazon.com/)
- [AWS Support](https://console.aws.amazon.com/support/home#/)
