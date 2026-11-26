**To list distribution configurations that match a name filter**

The following ``list-distribution-configurations`` example lists the distribution configurations in your account, filtered to a specific configuration by name. ::

    aws imagebuilder list-distribution-configurations \
        --filters name=name,values=my-example-distribution-configuration

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "distributionConfigurationSummaryList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:distribution-configuration/my-example-distribution-configuration",
                "name": "my-example-distribution-configuration",
                "description": "Distributes AMIs to us-west-2",
                "dateCreated": "2026-09-09T21:09:02.581Z",
                "tags": {},
                "regions": [
                    "us-west-2"
                ]
            }
        ]
    }

For more information, see `List and view distribution configuration detail <https://docs.aws.amazon.com/imagebuilder/latest/userguide/distribution-settings-detail.html>`__ in the *EC2 Image Builder User Guide*.
