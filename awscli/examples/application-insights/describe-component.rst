**To describe a component and its resources in an application**

This example uses the ``describe-component`` command to describe a component and lists the resources that are grouped together in a component. Note: The component name is the ARN of the component and not the resource's name. ::

    aws application-insights describe-component \
        --resource-group-name MYEC2 \
        --component-name arn:aws:autoscaling:eu-west-1:123456789012:autoScalingGroup:abcd123e-853e-4b67-132a-bcd63ce2f03f:autoScalingGroupName/MyEC2ASG

Output::

    {
        "ApplicationComponent": {
            "ComponentName": "arn:aws:autoscaling:eu-west-1:123456789012:autoScalingGroup:abcd123e-853e-4b67-132a-bcd63ce2f03f:autoScalingGroupName/MyEC2ASG",
            "ResourceType": "AWS::AutoScaling::AutoScalingGroup",
            "OsType": "LINUX",
            "Tier": "DEFAULT",
            "Monitor": true,
            "DetectedWorkload": {
                "DEFAULT": {
                    "Priority": "1"
                }
            }
        },
        "ResourceList": []
    }