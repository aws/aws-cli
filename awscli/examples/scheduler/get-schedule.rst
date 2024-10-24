**To retrieve the specified schedule**

The following ``get-schedule`` will retrieve the specified schedule. ::

	aws scheduler get-schedule \
		--name DailySNSFunction

Ouput ::

	{
		"ActionAfterCompletion": "NONE",
		"Arn": "arn:aws:scheduler:ca-central-1:123456789012:schedule/default/DailySNSFunction",
		"CreationDate": "2024-10-15T14:46:32.507000+00:00",
		"FlexibleTimeWindow": {
			"Mode": "OFF"
		},
		"GroupName": "default",
		"LastModificationDate": "2024-10-15T14:46:32.507000+00:00",
		"Name": "DailySNSFunction",
		"ScheduleExpression": "cron(15 10 ? * 6L *)",
		"ScheduleExpressionTimezone": "UTC",
		"State": "ENABLED",
		"Target": {
			"Arn": "arn:aws:sns:ca-central-1:123456789012:TestingSNS",
			"RetryPolicy": {
				"MaximumEventAgeInSeconds": 86400,
				"MaximumRetryAttempts": 185
			},
			"RoleArn": "arn:aws:iam::123456789012:role/service-role/Amazon_EventBridge_Scheduler_SNS_32b911da8f"
		}
	}

For more information, see `Schedule types in EventBridge Scheduler <https://docs.aws.amazon.com/scheduler/latest/UserGuide/schedule-types.html>`__ in the *Amazon EventBridge Scheduler User Guide*.