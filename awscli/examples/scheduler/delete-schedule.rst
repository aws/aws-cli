**To delete the specified schedule**

The following ``delete-schedule`` deletes the specified schedule. If the command succeeds, no output is returned. ::

	aws scheduler delete-schedule \
		--name DailyLambda

For more information, see `Deleting a schedule in EventBridge Scheduler <https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule-delete.html>`__ in the *Amazon EventBridge Scheduler User Guide*.