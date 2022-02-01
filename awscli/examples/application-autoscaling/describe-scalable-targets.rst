**To describe scalable targets**

The following ``describe-scalable-targets`` example command displays details for the the scalable targets for the ``ecs`` service namespace::

    aws application-autoscaling describe-scalable-targets \
        --service-namespace ecs

Output::

    {
        "ScalableTargets": [
            {
                "ScalableDimension": "ecs:service:DesiredCount",
                "ResourceId": "service/default/web-app",
                "RoleARN": "arn:aws:iam::123456789012:role/ApplicationAutoscalingECSRole",
                "SuspendedState": {
                    "DynamicScalingOutSuspended": false,
                    "ScheduledScalingSuspended": false,
                    "DynamicScalingInSuspended": false
                },
                "CreationTime": 1462558906.199,
                "MinCapacity": 1,
                "ServiceNamespace": "ecs",
                "MaxCapacity": 10
            }
        ]
    }    

For more information, see `What Is Application Auto Scaling? <https://docs.aws.amazon.com/autoscaling/application/userguide/what-is-application-auto-scaling.html>`__ in the *Application Auto Scaling User Guide*.
