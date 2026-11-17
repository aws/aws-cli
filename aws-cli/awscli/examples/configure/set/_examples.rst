**To set configuration values**

The following ``set`` example sets configuration values. Given an empty config file, run the following commands. ::

    aws configure set aws_access_key_id default_access_key
    aws configure set aws_secret_access_key default_secret_key
    aws configure set default.region us-west-2
    aws configure set default.ca_bundle /path/to/ca-bundle.pem
    aws configure set region us-west-1 \
        --profile testing
    aws configure set profile.testing2.region eu-west-1

This command produces no output.

These commands produce the following config file::

    [default]
    region = us-west-2
    ca_bundle = /path/to/ca-bundle.pem

    [profile testing]
    region = us-west-1

    [profile testing2]
    region = eu-west-1

and the following ``~/.aws/credentials`` file::

    [default]
    aws_access_key_id = default_access_key
    aws_secret_access_key = default_secret_key

To perform bulk profiles update ``list-profiles`` command can be piped with ``set`` command.
To update the region for all profiles, use the following command. ::

    aws configure list-profiles | xargs -I {} aws configure set region us-west-2 --profile {}

will produce the following updated config file::

    [default]
    region = us-west-2
    ca_bundle = /path/to/ca-bundle.pem

    [profile testing]
    region = us-west-2

    [profile testing2]
    region = us-west-2

To update the profiles that match the pattern "testing*", use the following command. ::

    aws configure list-profiles | grep 'testing*' | xargs -I {} aws configure set cli_pager '' --profile {}

will produce the following updated config file::

    [default]
    region = us-west-2
    ca_bundle = /path/to/ca-bundle.pem

    [profile testing]
    region = us-west-2
    cli_pager =

    [profile testing2]
    region = us-west-2
    cli_pager =

To set a parameter in a sub-section, use one of the available sub-section parameters (``--services`` or ``--sso-session``).

For example, to set the ``sso_start_url`` in the ``my-sso-session`` SSO session sub-section, use the following command. ::

    aws configure set sso_start_url https://my-sso-portal.awsapps.com/start \
        --sso-session my-sso-session

To set a nested property, use dotted notation for the parameter name along with a sub-section parameter.
For example, to set a service-specific endpoint URL for EC2 in a services sub-section called ``my-services``, use the following command. ::

    aws configure set ec2.endpoint_url http://localhost:4567 \
        --services my-services

For more information, see `Configuration and credential file settings in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html>`__ in the *AWS CLI User Guide*.
