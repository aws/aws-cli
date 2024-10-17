**To create a scheduler**

The following ``create-schedule`` will create a scheduler. ::

	aws scheduler create-schedule \
		--name DailySNSFunction \
		--schedule-expression "cron(15 10 ? * 6L *)" \
		--flexible-time-window '{"Mode": "OFF"}' \
		--target '{"Arn": "arn:aws:sns:ca-central-1:123456789012:TestingSNS", "RoleArn": "arn:aws:iam::123456789012:role/service-role/Amazon_EventBridge_Scheduler_SNS_32b911da8f"}'

Ouput ::

	{
		"ScheduleArn": "arn:aws:scheduler:ca-central-1:123456789012:schedule/default/DailySNSFunction"
	}
	
For more information, see `Create a schedule using the AWS CLI <https://docs.aws.amazon.com/scheduler/latest/UserGuide/getting-started.html#getting-started-console>`__ in the *EventBridge Scheduler User Guide*.