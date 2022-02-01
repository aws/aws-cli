**To create a capacity provider**

The following ``create-capacity-provider`` example creates a capacity provider that uses an Auto Scaling group named ``MyAutoScalingGroup``, has managed scaling and managed termination protection enabled. This configuration is used for Amazon ECS cluster auto scaling. ::

    aws ecs create-capacity-provider \
        --name "MyCapacityProvider" \
        --auto-scaling-group-provider autoScalingGroupArn=arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:autoScalingGroupName/MyAutoScalingGroup,managedScaling={status=ENABLED,targetCapacity=100,minimumScalingStepSize=1,maximumScalingStepSize=100},managedTerminationProtection=ENABLED

Output::

    {
        "capacityProvider": {
            "capacityProviderArn": "arn:aws:ecs:us-west-2:123456789012:capacity-provider/MyCapacityProvider",
            "name": "MyCapacityProvider",
            "status": "ACTIVE",
            "autoScalingGroupProvider": {
                "autoScalingGroupArn": "arn:aws:autoscaling:us-west-2:123456789012:autoScalingGroup:a1b2c3d4-5678-90ab-cdef-EXAMPLE11111:autoScalingGroupName/MyAutoScalingGroup",
                "managedScaling": {
                    "status": "ENABLED",
                    "targetCapacity": 100,
                    "minimumScalingStepSize": 1,
                    "maximumScalingStepSize": 100
                },
                "managedTerminationProtection": "ENABLED"
            },
            "tags": []
        }
    }

For more information, see `Cluster auto scaling <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cluster-auto-scaling.html>`__ in the *Amazon ECS Developer Guide*.