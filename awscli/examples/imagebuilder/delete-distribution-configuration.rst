**To delete a distribution configuration**

The following ``delete-distribution-configuration`` example deletes the specified distribution configuration. ::

    aws imagebuilder delete-distribution-configuration \
        --distribution-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:distribution-configuration/my-example-distribution-configuration

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "distributionConfigurationArn": "arn:aws:imagebuilder:us-west-2:123456789012:distribution-configuration/my-example-distribution-configuration"
    }

For more information, see `Delete outdated or unused Image Builder resources <https://docs.aws.amazon.com/imagebuilder/latest/userguide/delete-resources.html>`__ in the *EC2 Image Builder User Guide*.
