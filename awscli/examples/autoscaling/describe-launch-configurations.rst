**To describe Auto Scaling launch configurations**

This example describes the specified launch configuration::

    aws autoscaling describe-launch-configurations --launch-configuration-names my-launch-config

The following is example output::

    {
        "LaunchConfigurations": [
            {
                "UserData": null,
                "EbsOptimized": false,
                "LaunchConfigurationARN": "arn:aws:autoscaling:us-west-2:123456789012:launchConfiguration:98d3b196-4cf9-4e88-8ca1-8547c24ced8b:launchConfigurationName/my-launch-config",
                "InstanceMonitoring": {
                    "Enabled": true
                },
                "ImageId": "ami-043a5034",
                "CreatedTime": "2014-05-07T17:39:28.599Z",
                "BlockDeviceMappings": [],
                "KeyName": null,
                "SecurityGroups": [
                    "sg-67ef0308"
                ],
                "LaunchConfigurationName": "my-launch-config",
                "KernelId": null,
                "RamdiskId": null,
                "InstanceType": "t1.micro",
                "AssociatePublicIpAddress": true
            }
        ]
    }

To return a specific number of launch configurations, use the ``max-items`` parameter::

    aws autoscaling describe-launch-configurations --max-items 1

The following is example output::

    {
        "NextToken": "Z3M3LMPEXAMPLE",
        "LaunchConfigurations": [
            {
                "UserData": null,
                "EbsOptimized": false,
                "LaunchConfigurationARN": "arn:aws:autoscaling:us-west-2:123456789012:launchConfiguration:98d3b196-4cf9-4e88-8ca1-8547c24ced8b:launchConfigurationName/my-launch-config",
                "InstanceMonitoring": {
                    "Enabled": true
                },
                "ImageId": "ami-043a5034",
                "CreatedTime": "2014-05-07T17:39:28.599Z",
                "BlockDeviceMappings": [],
                "KeyName": null,
                "SecurityGroups": [
                    "sg-67ef0308"
                ],
                "LaunchConfigurationName": "my-launch-config",
                "KernelId": null,
                "RamdiskId": null,
                "InstanceType": "t1.micro",
                "AssociatePublicIpAddress": true
            }
        ]
    }

If the output includes a ``NextToken`` field, there are more launch configurations. To get the additional launch configurations, use the value of this field with the ``starting-token`` parameter in a subsequent call as follows::

    aws autoscaling describe-launch-configurations --starting-token Z3M3LMPEXAMPLE
