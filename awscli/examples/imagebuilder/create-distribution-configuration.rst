**Example 1: To create a distribution configuration**

The following ``create-distribution-configuration`` example creates a distribution configuration that distributes the output AMI to two Regions. The AMI name includes the build date, so that repeated builds create unique AMI names. ::

    aws imagebuilder create-distribution-configuration \
        --name my-example-distribution \
        --description "Copies the output AMI to a second Region" \
        --distributions file://distribution-settings.json \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``distribution-settings.json``::

    [
        {
            "region": "us-west-2",
            "amiDistributionConfiguration": {
                "name": "my-example-image-{{ imagebuilder:buildDate }}"
            }
        },
        {
            "region": "us-east-1",
            "amiDistributionConfiguration": {
                "name": "my-example-image-{{ imagebuilder:buildDate }}"
            }
        }
    ]

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "distributionConfigurationArn": "arn:aws:imagebuilder:us-west-2:123456789012:distribution-configuration/my-example-distribution"
    }

**Example 2: To create a distribution configuration with launch permissions and a launch template update**

The following ``create-distribution-configuration`` example creates a distribution configuration that distributes the output AMI to two Regions. In us-east-1, it shares the AMI with another AWS account. In us-west-2, it sets the new AMI as the default version of your launch template. ::

    aws imagebuilder create-distribution-configuration \
        --name my-example-distribution \
        --description "Distributes the output AMI to two Regions and shares it with another account" \
        --distributions file://distributions.json \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``distributions.json``::

    [
        {
            "region": "us-west-2",
            "amiDistributionConfiguration": {
                "name": "my-example-image-{{ imagebuilder:buildDate }}"
            },
            "launchTemplateConfigurations": [
                {
                    "launchTemplateId": "lt-1234567890abcdef0",
                    "setDefaultVersion": true
                }
            ]
        },
        {
            "region": "us-east-1",
            "amiDistributionConfiguration": {
                "name": "my-example-image-{{ imagebuilder:buildDate }}",
                "launchPermission": {
                    "userIds": ["123456789111"]
                }
            }
        }
    ]

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "clientToken": "a1b2c3d4-5678-90ab-cdef-EXAMPLE22222",
        "distributionConfigurationArn": "arn:aws:imagebuilder:us-west-2:123456789012:distribution-configuration/my-example-distribution"
    }

For more information, see `Create and update AMI distribution configurations <https://docs.aws.amazon.com/imagebuilder/latest/userguide/cr-upd-ami-distribution-settings.html>`__ in the *EC2 Image Builder User Guide*.
