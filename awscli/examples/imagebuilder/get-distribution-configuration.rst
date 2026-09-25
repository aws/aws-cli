**To get the details of a distribution configuration**

The following ``get-distribution-configuration`` example retrieves a distribution configuration that distributes the output AMI to two Regions. ::

    aws imagebuilder get-distribution-configuration \
        --distribution-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:distribution-configuration/my-example-distribution

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "distributionConfiguration": {
            "arn": "arn:aws:imagebuilder:us-west-2:123456789012:distribution-configuration/my-example-distribution",
            "name": "my-example-distribution",
            "description": "Copies the output AMI to a second Region",
            "distributions": [
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
            ],
            "timeoutMinutes": 720,
            "dateCreated": "2026-09-09T19:37:37.231Z",
            "tags": {}
        }
    }

For more information, see `List and view distribution configuration detail <https://docs.aws.amazon.com/imagebuilder/latest/userguide/distribution-settings-detail.html>`__ in the *EC2 Image Builder User Guide*.
