**To get the launch configuration for a source server**

The following ``get-launch-configuration`` example gets the launch configuration for the specified source server. ::

    aws drs get-launch-configuration \
        --source-server-id s-1234567890abcdef0

Output::

    {
        "copyPrivateIp": false,
        "copyTags": false,
        "ec2LaunchTemplateID": "lt-0123456789abcdef0",
        "launchDisposition": "STARTED",
        "launchIntoInstanceProperties": {},
        "licensing": {
            "osByol": false
        },
        "name": "Launch Configuration for Source Server s-1234567890abcdef0",
        "postLaunchEnabled": false,
        "sourceServerID": "s-1234567890abcdef0",
        "targetInstanceTypeRightSizingMethod": "NONE"
    }

For more information, see `Configuring launch settings <https://docs.aws.amazon.com/drs/latest/userguide/launch-settings.html>`__ in the *AWS Elastic Disaster Recovery User Guide*.
