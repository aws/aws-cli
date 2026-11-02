**To delete a lifecycle hook**

The following ``delete-lifecycle-hook`` example deletes the specified lifecycle hook. ::

    aws autoscaling delete-lifecycle-hook \
        --lifecycle-hook-name my-lifecycle-hook \
        --auto-scaling-group-name my-asg

This command produces no output.

For more information, see `Amazon EC2 Auto Scaling lifecycle hooks <https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
