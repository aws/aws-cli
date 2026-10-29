**To delete a scheduled action from an Auto Scaling group**

The following ``delete-scheduled-action`` example deletes the specified scheduled action from the specified Auto Scaling group. ::

    aws autoscaling delete-scheduled-action \
        --auto-scaling-group-name my-asg \
        --scheduled-action-name my-scheduled-action

This command produces no output.

For more information, see `Scheduled scaling for Amazon EC2 Auto Scaling <https://docs.aws.amazon.com/autoscaling/ec2/userguide/ec2-auto-scaling-scheduled-scaling.html>`__ in the *Amazon EC2 Auto Scaling User Guide*.
