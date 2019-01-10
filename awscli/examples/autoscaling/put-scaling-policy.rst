**To add a scaling policy to an Auto Scaling group**

This example adds a simple scaling policy to the specified Auto Scaling group::

    aws autoscaling put-scaling-policy --auto-scaling-group-name my-auto-scaling-group --policy-name ScaleIn --scaling-adjustment -1 --adjustment-type ChangeInCapacity

To change the size of the Auto Scaling group by a specific number of instances, set the ``adjustment-type`` parameter to ``PercentChangeInCapacity``. Then, assign a value to
the ``min-adjustment-step`` parameter, where the value represents the number of instances the policy adds or removes from the Auto Scaling group::

    aws autoscaling put-scaling-policy --auto-scaling-group-name my-auto-scaling-group --policy-name ScalePercentChange --scaling-adjustment 25 --adjustment-type PercentChangeInCapacity --cooldown 60 --min-adjustment-step 2

The output includes the ARN of the policy. The following is example output::

    {
        "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:2233f3d7-6290-403b-b632-93c553560106:autoScalingGroupName/my-auto-scaling-group:policyName/ScaleIn"
    }

For more information, see `Dynamic Scaling`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Dynamic Scaling`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/as-scale-based-on-demand.html
