:title: AWS CLI Configuration Variables
:description: Configuration Variables for the AWS CLI
:category: General
:related command: configure, configure get, configure set
:related topic: s3-config

Configuration values for the AWS CLI can come from several sources:

* As a command line option
* As an environment variable
* As a value in the AWS CLI config file
* As a value in the AWS Shared Credential file

Some options are only available in the AWS CLI config.  This topic guide covers
all the configuration variables available in the AWS CLI.

Note that if you are just looking to get the minimum required configuration to
run the AWS CLI, we recommend running ``aws configure``, which will prompt you
for the necessary configuration values.

Config File Format
==================

The AWS CLI config file, which defaults to ``~/.aws/config`` has the following
format::

    [default]
    aws_access_key_id=foo
    aws_secret_access_key=bar
    region=us-west-2

The ``default`` section refers to the configuration values for the default
profile.  You can create profiles, which represent logical groups of
configuration.  Profiles that aren't the default profile are specified by
creating a section titled "profile profilename"::

    [profile testing]
    aws_access_key_id=foo
    aws_secret_access_key=bar
    region=us-west-2

Nested Values
-------------

Some service specific configuration, discussed in more detail below, has a
single top level key, with nested sub values.  These sub values are denoted by
indentation::

    [profile testing]
    aws_access_key_id = foo
    aws_secret_access_key = bar
    region = us-west-2
    s3 =
      max_concurrent_requests=10
      max_queue_size=1000


General Options
===============

The AWS CLI has a few general options:

=========== ========= ===================== ===================== ============================
Variable    Option    Config Entry          Environment Variable  Description
=========== ========= ===================== ===================== ============================
profile     --profile N/A                   AWS_DEFAULT_PROFILE   Default profile name
----------- --------- --------------------- --------------------- ----------------------------
region      --region  region                AWS_DEFAULT_REGION    Default AWS Region
----------- --------- --------------------- --------------------- ----------------------------
output      --output  output                AWS_DEFAULT_OUTPUT    Default output style
=========== ========= ===================== ===================== ============================

The third column, Config Entry, is the value you would specify in the AWS CLI
config file.  By default, this location is ``~/.aws/config``.  If you need to
change this value, you can set the ``AWS_CONFIG_FILE`` environment variable
to change this location.

The valid values of the ``output`` configuration variable are:

* json
* table
* text

When you specify a profile, either using ``--profile profile-name`` or by
setting a value for the ``AWS_DEFAULT_PROFILE`` environment variable, profile
name you provide is used to find the corresponding section in the AWS CLI
config file.  For example, specifying ``--profile development`` will instruct
the AWS CLI to look for a section in the AWS CLI config file of
``[profile development]``.

Precedence
----------

The above configuration values have the following precedence:

* Command line options
* Environment variables
* Configuration file


Credentials
===========

Credentials can be specified in several ways:

* Environment variables
* The AWS Shared Credential File
* The AWS CLI config file

=========== ===================== ===================== ============================
Variable    Creds/Config Entry    Environment Variable  Description
=========== ===================== ===================== ============================
access_key  aws_access_key_id     AWS_ACCESS_KEY_ID     AWS Access Key
----------- --------------------- --------------------- ----------------------------
secret_key  aws_secret_access_key AWS_SECRET_ACCESS_KEY AWS Secret Key
----------- --------------------- --------------------- ----------------------------
token       aws_session_token     AWS_SESSION_TOKEN     AWS Token (temp credentials)
=========== ===================== ===================== ============================

The second column specifies the name that you can specify in either the AWS CLI
config file or the AWS Shared credentials file (``~/.aws/credentials``).


The Shared Credentials File
---------------------------

The shared credentials file has a fixed location of
``~/.aws/credentials``.  This file is an INI formatted file with section names
corresponding to profiles.  With each section, the three configuration
variables shown above can be specified: ``aws_access_key_id``,
``aws_secret_access_key``, ``aws_session_token``.  **These are the only
supported values in the shared credential file.**  Also note that the
section names are different than the AWS CLI config file (``~/.aws/config``).
In the AWS CLI config file, you create a new profile by creating a section of
``[profile profile-name]``, for example::

    [profile development]
    aws_access_key_id=foo
    aws_secret_access_key=bar

In the shared credentials file, profiles are not prefixed with ``profile``,
for example::

    [development]
    aws_access_key_id=foo
    aws_secret_access_key=bar


Precedence
----------

Credentials from environment variables have precedence over credentials from
the shared credentials and AWS CLI config file.  Credentials specified in the
shared credentials file have precedence over credentials in the AWS CLI config
file.


Using AWS IAM Roles
-------------------

If you are on an Amazon EC2 instance that was launched with an IAM role, the
AWS CLI will automatically retrieve credentials for you.  You do not need
to configure any credentials.

Additionally, you can specify a role for the AWS CLI to assume, and the AWS
CLI will automatically make the corresponding ``AssumeRole`` calls for you.
Note that configuration variables for using IAM roles can only be in the AWS
CLI config file.

You can specify the following configuration values for configuring an IAM role
in the AWS CLI config file:

* ``role_arn`` - The ARN of the role you want to assume.
* ``source_profile`` - The AWS CLI profile that contains credentials we should
  use for the initial ``assume-role`` call.
* ``external_id`` - A unique identifier that is used by third parties to assume
  a role in their customers' accounts.  This maps to the ``ExternalId``
  parameter in the ``AssumeRole`` operation.  This is an optional parameter.
* ``mfa_serial`` - The identification number of the MFA device to use when
  assuming a role.  This is an optional parameter.  Specify this value if the
  trust policy of the role being assumed includes a condition that requires MFA
  authentication. The value is either the serial number for a hardware device
  (such as GAHT12345678) or an Amazon Resource Name (ARN) for a virtual device
  (such as arn:aws:iam::123456789012:mfa/user).

If you do not have MFA authentication required, then you only need to specify a
``role_arn`` and a ``source_profile``.

When you specify a profile that has IAM role configuration, the AWS CLI
will make an ``AssumeRole`` call to retrieve temporary credentials.  These
credentials are then stored (in ``~/.aws/cache``).  Subsequent AWS CLI commands
will use the cached temporary credentials until they expire, in which case the
AWS CLI will automatically refresh credentials.

If you specify an ``mfa_serial``, then the first time an ``AssumeRole`` call is
made, you will be prompted to enter the MFA code.  Subsequent commands will use
the cached temporary credentials.  However, when the temporary credentials
expire, you will be re-prompted for another MFA code.


Example configuration::

  # In ~/.aws/credentials:
  [development]
  aws_access_key_id=foo
  aws_access_key_id=bar

  # In ~/.aws/config
  [profile crossaccount]
  role_arn=arn:aws:iam:...
  source_profile=development


Service Specific Configuration
==============================


aws s3
------

These values are only applicable for the ``aws s3`` commands.  These
configuration values are sub values that must be specified under the top level
``s3`` key.

These are the configuration values you can set for S3:

* ``max_concurrent_requests`` - The maximum number of concurrent requests.
* ``max_queue_size`` - The maximum number of tasks in the task queue.
* ``multipart_threshold`` - The size threshold where the CLI uses multipart
  transfers.
* ``multipart_chunksize`` - When using multipart transfers, this is the chunk
  size that will be used.

Example config::

    [profile development]
    aws_access_key_id=foo
    aws_secret_access_key=bar
    s3 =
      max_concurrent_requests = 20
      max_queue_size = 10000
      multipart_threshold = 64MB
      multipart_chunksize = 16MB


For a more in depth discussion of these S3 configuration values, see ``aws help
s3-config``.
