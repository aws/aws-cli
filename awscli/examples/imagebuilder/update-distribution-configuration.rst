**To update a distribution configuration**

The following ``update-distribution-configuration`` example replaces the distribution settings for the specified configuration with a single distribution that names the output AMI with the build date. ::

    aws imagebuilder update-distribution-configuration \
        --distribution-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:distribution-configuration/my-example-distribution \
        --distributions file://distribution-settings.json \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Contents of ``distribution-settings.json``::

    [
        {
            "region": "us-west-2",
            "amiDistributionConfiguration": {
                "name": "my-example-image-{{ imagebuilder:buildDate }}"
            }
        }
    ]

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "distributionConfigurationArn": "arn:aws:imagebuilder:us-west-2:123456789012:distribution-configuration/my-example-distribution"
    }

For more information, see `Create and update AMI distribution configurations <https://docs.aws.amazon.com/imagebuilder/latest/userguide/cr-upd-ami-distribution-settings.html>`__ in the *EC2 Image Builder User Guide*.
