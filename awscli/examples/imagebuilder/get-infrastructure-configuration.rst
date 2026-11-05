**To get the details of an infrastructure configuration**

The following ``get-infrastructure-configuration`` example retrieves an infrastructure configuration that specifies the instance types, instance profile, and instance metadata options that Image Builder uses for build and test instances. ::

    aws imagebuilder get-infrastructure-configuration \
        --infrastructure-configuration-arn arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure-configuration

Output::

    {
        "requestId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111",
        "infrastructureConfiguration": {
            "arn": "arn:aws:imagebuilder:us-west-2:123456789012:infrastructure-configuration/my-example-infrastructure-configuration",
            "name": "my-example-infrastructure-configuration",
            "description": "Infrastructure configuration for my application image builds",
            "instanceTypes": [
                "m5.large",
                "m5.xlarge"
            ],
            "instanceProfileName": "EC2InstanceProfileForImageBuilder",
            "terminateInstanceOnFailure": true,
            "dateCreated": "2026-09-09T19:36:48.933Z",
            "resourceTags": {
                "CostCenter": "12345"
            },
            "instanceMetadataOptions": {
                "httpTokens": "required",
                "httpPutResponseHopLimit": 2
            },
            "tags": {
                "Environment": "test"
            }
        }
    }

For more information, see `List and view infrastructure configuration details <https://docs.aws.amazon.com/imagebuilder/latest/userguide/infra-config-details.html>`__ in the *EC2 Image Builder User Guide*.
