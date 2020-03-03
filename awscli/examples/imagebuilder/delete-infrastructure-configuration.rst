**To delete an infrastructure configuration**

The following ``delete-infrastructure-configuration`` example deletes the specified image pipeline. ::

    aws imagebuilder delete-infrastructure-configuration \
        --infrastructure-configuration-arn arn:aws:imagebuilder:us-east-1:123456789012:infrastructure-configuration/myexampleinfrastructure

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "infrastructureConfigurationArn": "arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/myexampleinfrastructure"
    }

For more information, see `Setting Up and Managing an EC2 Image Builder Image Pipeline Using the AWS CLI` <https://https://docs.aws.amazon.com/imagebuilder/latest/userguide/managing-image-builder-cli.html>`__ in the *EC2 Image Builder Users Guide*.
