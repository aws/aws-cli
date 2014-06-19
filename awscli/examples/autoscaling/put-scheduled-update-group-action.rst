**To add a scheduled action to an Auto Scaling group**

The following ``put-scheduled-update-group-action`` command adds a scheduled action to an Auto Scaling group::

	aws autoscaling put-scheduled-update-group-action --auto-scaling-group-name basic-auto-scaling-group --scheduled-action-name sample-scheduled-action --start-time "2014-05-12T08:00:00Z" --end-time "2014-05-12T08:00:00Z" --min-size 2 --max-size 6 --desired-capacity 4

The following example creates a scheduled action to scale on a recurring schedule that is scheduled to execute at 00:30 hours on the first of January, June, and December every year::

	aws autoscaling put-scheduled-update-group-action --auto-scaling-group-name basic-auto-scaling-group --scheduled-action-name sample-scheduled-action --recurrence "30 0 1 1,6,12 0" --min-size 2 --max-size 6 --desired-capacity 4

For more information, see `Scheduled Scaling`_ in the *Auto Scaling Developer Guide*.

.. _`Scheduled Scaling`: http://docs.aws.amazon.com/AutoScaling/latest/DeveloperGuide/schedule_time.html

