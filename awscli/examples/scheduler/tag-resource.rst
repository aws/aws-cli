**To assigns one or more tags (key-value pairs) to the specified EventBridge Scheduler resource**

The following ``tag-resource`` assigns one or more tags (key-value pairs) to the specified EventBridge Scheduler resource. If the command succeeds, no output is returned. ::

	aws scheduler tag-resource \
		--resource-arn "arn:aws:scheduler:ca-central-1:123456789012:schedule-group/test" \
		--tags Key=environment,Value=production

For more information, see `Changing the schedule state in EventBridge Scheduler <https://docs.aws.amazon.com/scheduler/latest/UserGuide/managing-schedule-state.html>`__ in the *Amazon EventBridge Scheduler User Guide*.