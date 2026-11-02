**To complete the lifecycle action**

The following ``complete-lifecycle-action`` example notifies Amazon EC2 Auto Scaling that the specified lifecycle action is complete so that it can finish launching or terminating the instance. ::

    aws autoscaling complete-lifecycle-action \
        --lifecycle-hook-name my-launch-hook \
        --auto-scaling-group-name my-asg \
        --lifecycle-action-result CONTINUE \
        --lifecycle-action-token a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Amazon EC2 Auto Scaling lifecycle hooks <https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
