**To update an infrastructure configuration**

The following ``update-infrastructure-configuration`` example updates an infrastructure configuration to use larger instance types and to keep the build instance running when the image build fails. ::

    aws imagebuilder update-infrastructure-configuration \
        --infrastructure-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure \
        --description "An infrastructure configuration for Amazon Linux builds" \
        --instance-profile-name EC2InstanceProfileForImageBuilder \
        --instance-types t3.large t3.xlarge \
        --no-terminate-instance-on-failure \
        --client-token a1b2c3d4-5678-90ab-cdef-EXAMPLE22222

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "infrastructureConfigurationArn": "arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure"
    }

For more information, see `Update an infrastructure configuration <https://docs.aws.amazon.com/imagebuilder/latest/userguide/update-infra-config.html>`__ in the *EC2 Image Builder User Guide*.
