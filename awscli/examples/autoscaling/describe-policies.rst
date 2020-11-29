**To describe scaling policies**

This example describes the policies for the specified Auto Scaling group. ::

    aws autoscaling describe-policies --auto-scaling-group-name my-asg

The following is example output::

    {
        "ScalingPolicies": [
            {
                "AutoScalingGroupName": "my-asg",
                "PolicyName": "alb1000-target-tracking-scaling-policy",
                "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:3065d9c8-9969-4bec-bb6a-3fbe5550fde6:autoScalingGroupName/my-asg:policyName/alb1000-target-tracking-scaling-policy",
                "PolicyType": "TargetTrackingScaling",
                "StepAdjustments": [],
                "Alarms": [
                    {
                        "AlarmName": "TargetTracking-my-asg-AlarmHigh-924887a9-12d7-4e01-8686-6f844d13a196",
                        "AlarmARN": "arn:aws:cloudwatch:us-west-2:123456789012:alarm:TargetTracking-my-asg-AlarmHigh-924887a9-12d7-4e01-8686-6f844d13a196"
                    },
                    {
                        "AlarmName": "TargetTracking-my-asg-AlarmLow-f96f899d-b8e7-4d09-a010-c1aaa35da296",
                        "AlarmARN": "arn:aws:cloudwatch:us-west-2:123456789012:alarm:TargetTracking-my-asg-AlarmLow-f96f899d-b8e7-4d09-a010-c1aaa35da296"
                    }
                ],
                "TargetTrackingConfiguration": {
                    "PredefinedMetricSpecification": {
                        "PredefinedMetricType": "ALBRequestCountPerTarget",
                        "ResourceLabel": "app/my-alb/778d41231b141a0f/targetgroup/my-alb-target-group/943f017f100becff"
                    },
                    "TargetValue": 1000.0,
                    "DisableScaleIn": false
                },
                "Enabled": true
            },
            {
                "AutoScalingGroupName": "my-asg",
                "PolicyName": "cpu40-target-tracking-scaling-policy",
                "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:5fd26f71-39d4-4690-82a9-b8515c45cdde:autoScalingGroupName/my-asg:policyName/cpu40-target-tracking-scaling-policy",
                "PolicyType": "TargetTrackingScaling",
                "StepAdjustments": [],
                "Alarms": [
                    {
                        "AlarmName": "TargetTracking-my-asg-AlarmHigh-139f9789-37b9-42ad-bea5-b5b147d7f473",
                        "AlarmARN": "arn:aws:cloudwatch:us-west-2:123456789012:alarm:TargetTracking-my-asg-AlarmHigh-139f9789-37b9-42ad-bea5-b5b147d7f473"
                    },
                    {
                        "AlarmName": "TargetTracking-my-asg-AlarmLow-bd681c67-fc18-4c56-8468-fb8e413009c9",
                        "AlarmARN": "arn:aws:cloudwatch:us-west-2:123456789012:alarm:TargetTracking-my-asg-AlarmLow-bd681c67-fc18-4c56-8468-fb8e413009c9"
                    }
                ],
                "TargetTrackingConfiguration": {
                    "PredefinedMetricSpecification": {
                        "PredefinedMetricType": "ASGAverageCPUUtilization"
                    },
                    "TargetValue": 40.0,
                    "DisableScaleIn": false
                },
                "Enabled": true
            }
        ]
    }

To return specific scaling policies, use the ``policy-names`` parameter. ::

    aws autoscaling describe-policies --auto-scaling-group-name my-asg --policy-names cpu40-target-tracking-scaling-policy

To return a specific number of policies, use the ``max-items`` parameter. ::

    aws autoscaling describe-policies --auto-scaling-group-name my-asg --max-items 1

If the output includes a ``NextToken`` field, use the value of this field with the ``starting-token`` parameter in a subsequent call to get the additional policies. ::

    aws autoscaling describe-policies --auto-scaling-group-name my-asg --starting-token Z3M3LMPEXAMPLE

For more information, see `Dynamic scaling`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Dynamic scaling`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scale-based-on-demand.html
