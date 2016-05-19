**To describe Auto Scaling policies**

This example describes the policies for the specified Auto Scaling group::

    aws autoscaling describe-policies --auto-scaling-group-name my-auto-scaling-group

The following is example output::

    {
        "ScalingPolicies": [
            {
                "PolicyName": "ScaleIn",
                "AutoScalingGroupName": "my-auto-scaling-group",
                "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:2233f3d7-6290-403b-b632-93c553560106:autoScalingGroupName/my-auto-scaling-group:policyName/ScaleIn",
                "AdjustmentType": "ChangeInCapacity",
                "Alarms": [],
                "ScalingAdjustment": -1
            },
            {
                "PolicyName": "ScalePercentChange",
                "MinAdjustmentStep": 2,
                "AutoScalingGroupName": "my-auto-scaling-group",
                "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:2b435159-cf77-4e89-8c0e-d63b497baad7:autoScalingGroupName/my-auto-scaling-group:policyName/ScalePercentChange",
                "Cooldown": 60,
                "AdjustmentType": "PercentChangeInCapacity",
                "Alarms": [],
                "ScalingAdjustment": 25
            }
        ]
    }

To return specific scaling policies, use the ``policy-names`` parameter::

    aws autoscaling describe-policies --auto-scaling-group-name my-auto-scaling-group --policy-names ScaleIn

To return a specific number of policies, use the ``max-items`` parameter::

    aws autoscaling describe-policies --auto-scaling-group-name my-auto-scaling-group --max-items 1

The following is example output::

    {
        "ScalingPolicies": [
            {
                "PolicyName": "ScaleIn",
                "AutoScalingGroupName": "my-auto-scaling-group",
                "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:2233f3d7-6290-403b-b632-93c553560106:autoScalingGroupName/my-auto-scaling-group:policyName/ScaleIn",
                "AdjustmentType": "ChangeInCapacity",
                "Alarms": [],
                "ScalingAdjustment": -1
            }
        ],
        "NextToken": "Z3M3LMPEXAMPLE"
    }

If the output includes a ``NextToken`` field, use the value of this field with the ``starting-token`` parameter in a subsequent call to get the additional policies::

    aws autoscaling describe-policies --auto-scaling-group-name my-auto-scaling-group --starting-token Z3M3LMPEXAMPLE

For more information, see `Dynamic Scaling`_ in the *Auto Scaling Developer Guide*.

.. _`Dynamic Scaling`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/as-scale-based-on-demand.html
