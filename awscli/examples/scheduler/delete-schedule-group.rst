**To delete the specified schedule group**

The following ``delete-schedule-group`` deletes the specified schedule group. Deleting a schedule group results in EventBridge Scheduler deleting all schedules associated with the group. If the command succeeds, no output is returned. ::

	aws scheduler delete-schedule-group \
		--name DailyLambda

For more information, see `Deleting a schedule group in EventBridge Scheduler <https://docs.aws.amazon.com/scheduler/laDailyLambda/UserGuide/managing-schedule-group-delete.html>`__ in the *Amazon EventBridge Scheduler User Guide*.