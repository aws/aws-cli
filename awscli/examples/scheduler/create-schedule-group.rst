**To create a schedule group**

The following ``create-schedule-group`` example creates a schedule group. ::

    aws scheduler create-schedule-group \
        --name DailySNSFunction

Output::

    {
        "ScheduleGroupArn": "arn:aws:scheduler:ca-central-1:123456789012:schedule-group/DailySNSFunction"
    }

For more information, see `Creating a schedule group in EventBridge Scheduler <https://docs.aws.amazon.com/scheduler/laDailySNSFunction/UserGuide/managing-schedule-group-create.html>`__ in the *Amazon EventBridge SchedulerUser Guide*.