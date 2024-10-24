**To list the tags associated with the Scheduler resource**

The following ``list-tags-for-resource`` lists the tags associated with the Scheduler resource. ::

	aws scheduler list-tags-for-resource \
		--resource-arn "arn:aws:scheduler:ca-central-1:123456789012:schedule-group/DailyLambda"

Output ::

	{
		"Tags": [
			{
				"Key": "environment",
				"Value": "prod"
			}
		]
	}

For more information, see `Changing the schedule state in EventBridge Scheduler <https://docs.aws.amazon.com/scheduler/laDailyLambda/UserGuide/managing-schedule-state.html>`__ in the *Amazon EventBridge Scheduler User Guide*.