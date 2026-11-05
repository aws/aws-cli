**To set the desired capacity for an Auto Scaling group**

The following ``set-desired-capacity`` example sets the desired capacity for the specified Auto Scaling group. ::

    aws autoscaling set-desired-capacity \
        --auto-scaling-group-name my-asg \
        --desired-capacity 2 \
        --honor-cooldown

This command produces no output.

This command returns to the prompt if successful.

For more information, see `Manual scaling for Amazon EC2 Auto Scaling <https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-scaling-manually.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
