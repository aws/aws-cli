**To delete the specified schedule group**

The following ``delete-schedule-group`` example deletes the specified schedule group. Deleting a schedule group deletes all schedules associated with the group in EventBridge. ::

    aws scheduler delete-schedule-group \
        --name DailyLambda

This command produces no output.

For more information, see `Deleting a schedule group in EventBridge Scheduler <https://docs.aws.amazon.com/scheduler/laDailyLambda/UserGuide/managing-schedule-group-delete.html>`__ in the *Amazon EventBridge Scheduler User Guide*.