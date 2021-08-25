To generate an AWS Management Console signin URL with the default profile::

    $ aws signin

To generate an AWS Management Console signin URL with the my_role profile::

    $ aws --profile my_role signin

To go directly to the CloudFormation service page after login::

    $ aws signin --destination-url https://console.aws.amazon.com/cloudformation/home

To generate a signin link to AWS GovCloud::

    $ aws signin --partition AWS_US_GOV
