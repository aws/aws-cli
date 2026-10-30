**To describe scaling policies**

The following ``describe-scaling-policies`` example describes the scaling policies for the `ecs` service namespace. ::

    aws application-autoscaling describe-scaling-policies \
        --service-namespace ecs

Output::

    {
        "ScalingPolicies": [
            {
                "PolicyName": "web-app-cpu-gt-75",
                "ScalableDimension": "ecs:service:DesiredCount",
                "ResourceId": "service/default/web-app",
                "CreationTime": 1462561899.23,
                "StepScalingPolicyConfiguration": {
                    "Cooldown": 60,
                    "StepAdjustments": [
                        {
                            "ScalingAdjustment": 200,
                            "MetricIntervalLowerBound": 0.0
                        }
                    ],
                    "AdjustmentType": "PercentChangeInCapacity"
                },
                "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:resource/ecs/service/default/web-app:policyName/web-app-cpu-gt-75",
                "PolicyType": "StepScaling",
                "Alarms": [
                    {
                        "AlarmName": "web-app-cpu-gt-75",
                        "AlarmARN": "arn:aws:cloudwatch:us-west-2:123456789012:alarm:web-app-cpu-gt-75"
                    }
                ],
                "ServiceNamespace": "ecs"
            },
            {
                "PolicyName": "web-app-cpu-lt-25",
                "ScalableDimension": "ecs:service:DesiredCount",
                "ResourceId": "service/default/web-app",
                "CreationTime": 1462562575.099,
                "StepScalingPolicyConfiguration": {
                    "Cooldown": 1,
                    "StepAdjustments": [
                        {
                            "ScalingAdjustment": -50,
                            "MetricIntervalUpperBound": 0.0
                        }
                    ],
                    "AdjustmentType": "PercentChangeInCapacity"
                },
                "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:resource/ecs/service/default/web-app:policyName/web-app-cpu-lt-25",
                "PolicyType": "StepScaling",
                "Alarms": [
                    {
                        "AlarmName": "web-app-cpu-lt-25",
                        "AlarmARN": "arn:aws:cloudwatch:us-west-2:123456789012:alarm:web-app-cpu-lt-25"
                    }
                ],
                "ServiceNamespace": "ecs"
            }
        ]
    }

For more information, see `Describe step scaling policies for Application Auto Scaling using the AWS CLI <https://docs.aws.amazon.com/autoscaling/application/userguide/describe-step-scaling-policy.html>`__ in the *Application Auto Scaling User Guide*.
