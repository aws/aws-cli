**To describe launch configuration templates**

The following ``describe-launch-configuration-templates`` example describes all launch configuration templates in your account. ::

    aws drs describe-launch-configuration-templates

Output::

    {
        "items": [
            {
                "arn": "arn:aws:drs:us-west-2:123456789012:launch-configuration-template/lct-1234567890abcdef0",
                "copyPrivateIp": false,
                "copyTags": false,
                "exportBucketArn": "arn:aws:s3:::amzn-s3-demo-bucket",
                "launchConfigurationTemplateID": "lct-1234567890abcdef0",
                "launchDisposition": "STARTED",
                "launchIntoSourceInstance": false,
                "licensing": {
                    "osByol": false
                },
                "postLaunchEnabled": true,
                "tags": {},
                "targetInstanceTypeRightSizingMethod": "NONE"
            }
        ]
    }

For more information, see `Configuring launch settings <https://docs.aws.amazon.com/drs/latest/userguide/launch-settings.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
