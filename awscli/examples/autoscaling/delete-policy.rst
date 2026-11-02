**To delete a scaling policy**

The following ``delete-policy`` example deletes the specified scaling policy. ::

    aws autoscaling delete-policy \
        --auto-scaling-group-name my-asg \
        --policy-name alb1000-target-tracking-scaling-policy

This command produces no output.

For more information, see `Delete a scaling policy for an Auto Scaling group <https://docs.aws.amazon.com/autoscaling/ec2/userguide/deleting-scaling-policy.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
