Configure AWS CLI configuration data.  If this command is run with no
arguments, you will be prompted for configuration values such as your AWS
Access Key Id and you AWS Secret Access Key.  You can configure a specific
profile using the ``--profile`` argument.  If your config file does not exist
(the default location is ``~/.aws/config``), it will be automatically created
for you.  To keep an existing value, hit enter when prompted for the value.
When you are prompted for information, the current value will be displayed in
``[brackets]``.  If the config item has no value, it be displayed as
``[None]``.  Note that the ``configure`` command only work with values from the
config file.  It does not use any configuration values from environment
variables or the IAM role.

=======================
Configuration Variables
=======================

The following configuration variables are supported in the config file:

* **aws_access_key_id** - The AWS access key part of your credentials
* **aws_secret_access_key** - The AWS secret access key part of your credentials
* **aws_security_token** - The security token part of your credentials (session tokens only)
* **metadata_service_timeout** - The number of seconds to wait until the metadata service
  request times out.  This is used if you are using an IAM role to provide
  your credentials.
* **metadata_service_num_attempts** - The number of attempts to try to retrieve
  credentials.  If you know for certain you will be using an IAM role on an
  Amazon EC2 instance, you can set this value to ensure any intermittent
  failures are retried.  By default this value is 1.
