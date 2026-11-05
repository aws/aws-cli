**To cancel an instance refresh**

The following ``cancel-instance-refresh`` example cancels an in-progress instance refresh for the specified Auto Scaling group. ::

    aws autoscaling cancel-instance-refresh \
        --auto-scaling-group-name my-asg

Output::

    {
        "InstanceRefreshId": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Cancel an instance refresh <https://docs.aws.amazon.com/autoscaling/ec2/userguide/cancel-instance-refresh.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.