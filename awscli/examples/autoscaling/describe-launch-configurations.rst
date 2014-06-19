**To describe Auto Scaling launch configurations**

The following ``describe-launch-configurations`` command returns information about a specific launch configuration::

	aws autoscaling describe-launch-configurations --launch-configuration-names "basic-launch-config"

The output of this command is a JSON block that describes the launch configuration, similar to the following::

	{
		"LaunchConfigurations": [
			{
				"UserData": null,
				"EbsOptimized": false,
				"LaunchConfigurationARN": "arn:aws:autoscaling:us-west-2:896650972448:launchConfiguration:98d3b196-4cf9-4e88-8ca1-8547c24ced8b:launchConfigurationName/basic-launch-config",
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

In this example, the output of this command is a JSON block that describes the first launch configuration:

::

	{
		"NextToken": "None___1",
		"LaunchConfigurations": [
			{
				"UserData": null,
				"EbsOptimized": false,
				"LaunchConfigurationARN": "arn:aws:autoscaling:us-west-2:896650972448:launchConfiguration:98d3b196-4cf9-4e88-8ca1-8547c24ced8b:launchConfigurationName/basic-launch-config",
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

This JSON block includes a ``NextToken`` field. You can use the value of this field with the ``starting-token`` parameter to return additional launch configurations::

    aws autoscaling describe-launch-configurations --starting-token None___1

For more information, see `Launch Configurations`_ in the *Auto Scaling Developer Guide*.

.. _`Launch Configurations`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/WorkingWithLaunchConfig.html

