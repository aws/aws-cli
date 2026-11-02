**To get configuration values**

The following ``get`` examples read values from this config file::

    [default]
    aws_access_key_id=default_access_key
    aws_secret_access_key=default_secret_key

    [profile testing]
    aws_access_key_id=testing_access_key
    aws_secret_access_key=testing_secret_key
    region=us-west-2

    [profile my-dev-profile]
    services = my-services
    sso_session = my-sso
    sso_account_id = 123456789012
    sso_role_name = readOnly
    region = us-west-2
    output = json

    [sso-session my-sso]
    sso_region = us-west-2
    sso_start_url = https://my-sso-portal.awsapps.com/start
    sso_registration_scopes = sso:account:access

    [services my-services]
    ec2 =
        endpoint_url = http://localhost:4567/

The following commands would have the corresponding output::

    $ aws configure get aws_access_key_id
    default_access_key

    $ aws configure get default.aws_access_key_id
    default_access_key

    $ aws configure get aws_access_key_id --profile testing
    testing_access_key

    $ aws configure get profile.testing.aws_access_key_id
    testing_access_key

    $ aws configure get profile.does-not-exist
    $
    $ echo $?
    1

    $ aws configure get --profile my-dev-profile sso_account_id
    123456789012

    $ aws configure get --sso-session my-sso-session sso_region
    us-west-2

    $ aws configure get --services my-services ec2.endpoint_url
    http://localhost:4567

For more information, see `Configuration and credential file settings in the AWS CLI <https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html>`__ in the *AWS CLI User Guide*.
