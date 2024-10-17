**To remove one or more tags from the specified EventBridge Scheduler schedule group**

The following ``untag-resource`` removes one or more tags from the specified EventBridge Scheduler schedule group. If the command succeeds, no output is returned. ::

	aws scheduler untag-resource \
		--resource-arn "arn:aws:scheduler:ca-central-1:123456789012:schedule-group/DailyLambda" \
		--tag-keys "environment"

For more information, see `This is the topic title <https://docs.aws.amazon.com/eventbridge/laDailyLambda/userguide/eb-pipes.html>`__ in the *Amazon EventBridge User Guide*.