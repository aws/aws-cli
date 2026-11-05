**To list infrastructure configurations by name**

The following ``list-infrastructure-configurations`` example lists your infrastructure configurations, filtered to a specific resource name. ::

    aws imagebuilder list-infrastructure-configurations \
        --filters name=name,values=my-example-infrastructure-configuration

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "infrastructureConfigurationSummaryList": [
            {
                "arn": "arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure-configuration",
                "name": "my-example-infrastructure-configuration",
                "description": "An example infrastructure configuration for Amazon Linux builds",
                "dateCreated": "2026-09-09T19:37:17.350Z",
                "tags": {
                    "Environment": "test"
                },
                "instanceTypes": [
                    "m5.large",
                    "m5.xlarge"
                ],
                "instanceProfileName": "EC2InstanceProfileForImageBuilder"
            }
        ]
    }

For more information, see `List and view infrastructure configuration details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/infra-config-details.html>`__ in the *EC2 Image Builder User Guide*.
