**To create a launch configuration template**

The following ``create-launch-configuration-template`` example creates a launch configuration template with the specified settings. ::

    aws drs create-launch-configuration-template \
        --launch-disposition STARTED \
        --target-instance-type-right-sizing-method NONE \
        --copy-private-ip \
        --copy-tags

Output::

    {
        "launchConfigurationTemplate": {
            "arn": "arn:aws:drs:us-west-2:123456789012:launch-configuration-template/lct-1234567890abcdef0",
            "copyPrivateIp": true,
            "copyTags": true,
            "launchConfigurationTemplateID": "lct-1234567890abcdef0",
            "launchDisposition": "STARTED",
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
