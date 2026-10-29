**To attach an instance to an Auto Scaling group**

The following ``attach-instances`` example attaches the specified instance to the specified Auto Scaling group. ::

    aws autoscaling attach-instances \
        --instance-ids i-061c63c5eb45f0416 \
        --auto-scaling-group-name my-asg

This command produces no output.

For more information, see `Detach or attach instances from your Auto Scaling group <https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-detach-attach-instances.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
