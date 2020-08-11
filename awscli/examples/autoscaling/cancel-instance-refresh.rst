**To cancel an instance refresh**

The following ``cancel-instance-refresh`` example cancels an instance refresh operation in progress. ::

    aws autoscaling cancel-instance-refresh \
        --auto-scaling-group-name my-asg

Output::

    {
        "InstanceRefreshId": "08b91cf7-8fa6-48af-b6a6-d227f40f1b9b"
    }

For more information, see `Replacing Auto Scaling Instances Based on an Instance Refresh <https://docs.aws.amazon.com/autoscaling/ec2/userguide/asg-instance-refresh.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.