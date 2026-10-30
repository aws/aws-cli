**To get the License Manager settings**

The following ``get-service-settings`` example displays the service settings for License Manager in the current Region. ::

    aws license-manager get-service-settings

The following shows example output if cross-account resource discovery is disabled.

Output::

    {
        "OrganizationConfiguration": {
            "EnableIntegration": false
        },
        "EnableCrossAccountsDiscovery": false
    }

The following shows example output if cross-account resource discovery is enabled.

Output::

    {
        "S3BucketArn": "arn:aws:s3:::aws-license-manager-service-c22d6279-35c4-47c4-bb",
        "OrganizationConfiguration": {
            "EnableIntegration": true
        },
        "EnableCrossAccountsDiscovery": true
    }

For more information, see `Settings in License Manager <https://docs.aws.amazon.com/license-manager/latest/userguide/settings.html>`__ in the *AWS License Manager User Guide*.
