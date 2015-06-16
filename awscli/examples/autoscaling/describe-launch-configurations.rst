**To describe Auto Scaling launch configurations**

This example returns information about the specified launch configuration::

	aws autoscaling describe-launch-configurations --launch-configuration-names "basic-launch-config"

The following is example output for this command::

	{
		"LaunchConfigurations": [
			{
				"UserData": null,
				"EbsOptimized": false,
				"LaunchConfigurationARN": "arn:aws:autoscaling:us-west-2:123456789012:launchConfiguration:98d3b196-4cf9-4e88-8ca1-8547c24ced8b:launchConfigurationName/basic-launch-config",
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
				"LaunchConfigurationName": "basic-launch-config",
				"KernelId": null,
				"RamdiskId": null,
				"InstanceType": "t1.micro",
				"AssociatePublicIpAddress": true
			}
		]
	}

To return a specific number of launch configurations with this command, use the ``max-items`` parameter::

	aws autoscaling describe-launch-configurations --max-items 1

The following is example output for this command::

	{
		"NextToken": "None___1",
		"LaunchConfigurations": [
			{
				"UserData": null,
				"EbsOptimized": false,
				"LaunchConfigurationARN": "arn:aws:autoscaling:us-west-2:123456789012:launchConfiguration:98d3b196-4cf9-4e88-8ca1-8547c24ced8b:launchConfigurationName/basic-launch-config",
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
				"LaunchConfigurationName": "basic-launch-config",
				"KernelId": null,
				"RamdiskId": null,
				"InstanceType": "t1.micro",
				"AssociatePublicIpAddress": true
			}
		]
	}

The output includes a ``NextToken`` field. You can use the value of this field with the ``starting-token`` parameter to return additional launch configurations in a subsequent call::

    aws autoscaling describe-launch-configurations --starting-token None___1
