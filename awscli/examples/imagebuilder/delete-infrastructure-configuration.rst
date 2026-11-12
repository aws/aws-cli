**To delete an infrastructure configuration**

The following ``delete-infrastructure-configuration`` example deletes the infrastructure configuration with the specified ARN. ::

    aws imagebuilder delete-infrastructure-configuration \
        --infrastructure-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "infrastructureConfigurationArn": "arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure"
    }

For more information, see `Delete an infrastructure configuration <https://docs.aws.amazon.com/imagebuilder/latest/userguide/delete-infra-config.html>`__ in the *EC2 Image Builder User Guide*.
