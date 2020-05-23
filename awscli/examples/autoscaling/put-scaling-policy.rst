**To add simple scaling policies to an Auto Scaling group**

This example adds a simple scaling policy to the specified Auto Scaling group::

    aws autoscaling put-scaling-policy --auto-scaling-group-name my-asg --policy-type SimpleScaling --policy-name my-simple-scale-in-policy --scaling-adjustment -1 --cooldown 180 --adjustment-type ChangeInCapacity

To change the size of the Auto Scaling group by a specific number of instances, set the ``adjustment-type`` parameter to ``PercentChangeInCapacity``. Then, assign a value to the ``min-adjustment-magnitude`` parameter, where the value represents the number of instances the policy adds or removes from the Auto Scaling group::

    aws autoscaling put-scaling-policy --auto-scaling-group-name my-asg --policy-type SimpleScaling --policy-name my-simple-scale-out-policy --scaling-adjustment 30 --adjustment-type PercentChangeInCapacity --min-adjustment-magnitude 2

The output includes the ARN of the policy. The following is example output::

    {
        "PolicyARN": "arn:aws:autoscaling:us-west-2:123456789012:scalingPolicy:2233f3d7-6290-403b-b632-93c553560106:autoScalingGroupName/my-asg:policyName/my-simple-scale-out-policy"
    }

For more information, see `Example Scaling Policies for the AWS Command Line Interface (AWS CLI)`_ in the *Amazon EC2 Auto Scaling User Guide*.

.. _`Example Scaling Policies for the AWS Command Line Interface (AWS CLI)`: https://docs.aws.amazon.com/autoscaling/ec2/userguide/examples-scaling-policies.html