**To list all components in an application**

This example uses the ``list-components`` command to list all the components in an application. ::

    aws application-insights list-components \
        --resource-group-name MYEC2

Output::

    {
        "ApplicationComponentList": [{
            "ComponentName": "arn:aws:ec2:us-east-1:123456789012:autoScalingGroup:bosy123f-853e-2b43-876c-bad63ce2f03f:autoScalingGroupName/MyEC2ASG",
            "ResourceType": "AWS::AutoScaling::AutoScalingGroup",
            "OsType": "LINUX",
            "Tier": "DEFAULT",
            "Monitor": true
        }, {
            "ComponentName": "arn:aws:ec2:us-east-1:123456789012:instance/i-012abcd34efghi56",
            "ResourceType": "AWS::EC2::Instance",
            "OsType": "WINDOWS",
            "Tier": "DEFAULT",
            "Monitor": true
        }]
    }