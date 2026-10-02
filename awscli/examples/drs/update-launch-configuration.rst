**To update the launch configuration for a source server**

The following ``update-launch-configuration`` example updates the launch disposition to ``STOPPED`` for the specified source server. ::

    aws drs update-launch-configuration \
        --source-server-id s-1234567890abcdef0 \
        --launch-disposition STOPPED

Output::

    {
        "copyPrivateIp": false,
        "copyTags": false,
        "ec2LaunchTemplateID": "lt-0123456789abcdef0",
        "launchDisposition": "STOPPED",
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
