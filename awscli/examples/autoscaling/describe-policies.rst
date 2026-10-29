**Example 1: To describe the scaling policies of a specified group**

The following ``describe-policies`` example describes the scaling policies for the specified Auto Scaling group. ::

    aws autoscaling describe-policies \
        --auto-scaling-group-name my-asg

Output::

    {
        "ScalingPolicies": [
            {
                "AutoScalingGroupName": "my-asg",
                "PolicyName": "alb1000-target-tracking-scaling-policy",
                "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:autoScalingGroupName/my-asg:policyName/alb1000-target-tracking-scaling-policy",
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
                "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222:autoScalingGroupName/my-asg:policyName/cpu40-target-tracking-scaling-policy",
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

For more information, see `Dynamic scaling <https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scale-based-on-demand.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 2: To describe the scaling policies of a specified name**

The following ``describe-policies`` example uses the ``--policy-names`` option to return specific scaling policies. ::

    aws autoscaling describe-policies \
        --auto-scaling-group-name my-asg \
        --policy-names cpu40-target-tracking-scaling-policy

Output::

    {
        "ScalingPolicies": [
            {
                "AutoScalingGroupName": "my-asg",
                "PolicyName": "cpu40-target-tracking-scaling-policy",
                "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:a1b2c3d4-5678-90ab-cdef-EXAMPLE22222:autoScalingGroupName/my-asg:policyName/cpu40-target-tracking-scaling-policy",
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

For more information, see `Dynamic scaling <https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scale-based-on-demand.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 3: To describe a number of scaling policies**

The following ``describe-policies`` example uses the ``--max-items`` option to return a specific number of policies. ::

    aws autoscaling describe-policies \
        --auto-scaling-group-name my-asg \
        --max-items 1

Output::

    {
        "ScalingPolicies": [
            {
                "AutoScalingGroupName": "my-asg",
                "PolicyName": "alb1000-target-tracking-scaling-policy",
                "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:autoScalingGroupName/my-asg:policyName/alb1000-target-tracking-scaling-policy",
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
            }
        ],
        "NextToken": "Z3M3LMPEXAMPLE"
    }

If the output includes a ``NextToken`` field, use the value of this field with the ``--starting-token`` option in a subsequent call to get the additional policies. ::

    aws autoscaling describe-policies \
        --auto-scaling-group-name my-asg \
        --starting-token Z3M3LMPEXAMPLE

For more information, see `Dynamic scaling <https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scale-based-on-demand.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
