**To set the desired capacity for an Auto Scaling group**

This example sets the desired capacity for the specified Auto Scaling group::

    aws autoscaling set-desired-capacity --auto-scaling-group-name my-auto-scaling-group --desired-capacity 2 --honor-cooldown
