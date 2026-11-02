**Example 1: To enable the instance protection setting for an instance**

The following ``set-instance-protection`` example enables instance protection for the specified instance. ::

    aws autoscaling set-instance-protection \
        --instance-ids i-061c63c5eb45f0416 \
        --auto-scaling-group-name my-asg \
        --protected-from-scale-in

This command produces no output.

For more information, see `Use instance scale-in protection to control instance termination <https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-instance-protection.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.

**Example 2: To disable the instance protection setting for an instance**

The following ``set-instance-protection`` example disables instance protection for the specified instance. ::

    aws autoscaling set-instance-protection \
        --instance-ids i-061c63c5eb45f0416 \
        --auto-scaling-group-name my-asg \
        --no-protected-from-scale-in

This command produces no output.

For more information, see `Use instance scale-in protection to control instance termination <https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-instance-protection.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
