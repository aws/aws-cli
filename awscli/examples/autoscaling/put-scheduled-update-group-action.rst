**To add a scheduled action to an Auto Scaling group**

This example adds the specified scheduled action to the specified Auto Scaling group::

    aws autoscaling put-scheduled-update-group-action --auto-scaling-group-name my-auto-scaling-group --scheduled-action-name my-scheduled-action --start-time "2014-05-12T08:00:00Z" --end-time "2014-05-12T08:00:00Z" --min-size 2 --max-size 6 --desired-capacity 4

This example creates a scheduled action to scale on a recurring schedule that is scheduled to execute at 00:30 hours on the first of January, June, and December every year::

    aws autoscaling put-scheduled-update-group-action --auto-scaling-group-name my-auto-scaling-group --scheduled-action-name my-scheduled-action --recurrence "30 0 1 1,6,12 *" --min-size 2 --max-size 6 --desired-capacity 4

For more information, see `Scheduled Scaling`__ in the *Amazon EC2 Auto Scaling User Guide*.

.. __: https://docs.aws.amazon.com/autoscaling/ec2/userguide/schedule_time.html
