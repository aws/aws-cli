**To update a launch configuration template**

The following ``update-launch-configuration-template`` example updates the launch disposition for the specified template. ::

    aws drs update-launch-configuration-template \
        --launch-configuration-template-id lct-1234567890abcdef0 \
        --launch-disposition STOPPED

Output::

    {
        "launchConfigurationTemplate": {
            "arn": "arn:aws:drs:us-west-2:123456789012:launch-configuration-template/lct-1234567890abcdef0",
            "copyPrivateIp": true,
            "copyTags": true,
            "launchConfigurationTemplateID": "lct-1234567890abcdef0",
            "launchDisposition": "STOPPED",
            "launchIntoSourceInstance": false,
            "licensing": {
                "osByol": false
            },
            "postLaunchEnabled": false,
            "tags": {},
            "targetInstanceTypeRightSizingMethod": "NONE"
        }
    }

For more information, see `Configuring launch settings <https://docs.aws.amazon.com/drs/latest/userguide/launch-settings.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
