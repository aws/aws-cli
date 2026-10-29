**To record a lifecycle action heartbeat**

The following ``record-lifecycle-action-heartbeat`` example records a lifecycle action heartbeat to keep the instance in a pending state. ::

    aws autoscaling record-lifecycle-action-heartbeat \
        --lifecycle-hook-name my-launch-hook \
        --auto-scaling-group-name my-asg \
        --lifecycle-action-token a1b2c3d4-5678-90ab-cdef-EXAMPLE11111

This command produces no output.

For more information, see `Amazon EC2 Auto Scaling lifecycle hooks <https://docs.aws.amazon.com/autoscaling/ec2/userguide/lifecycle-hooks.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

