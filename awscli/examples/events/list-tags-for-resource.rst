**To display the tags associated with an EventBridge resource**

The following ``list-tags-for-resource`` displays the tags associated with an EventBridge resource. In EventBridge, rules and event buses can be tagged. ::

	aws events list-tags-for-resource \
		--resource-arn "arn:aws:events:us-east-1:123456789012:rule/AlarmStateChange"

Output ::

	{
		"Tags": [
			{
				"Key": "Key1",
				"Value": "Value1"
			},
			{
				"Key": "Env",
				"Value": "Prod"
			}
			]
	}

For more information, see `Configure tags and review rule <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-rule-schedule.html#eb-create-scheduled-rule-review>`__ in the *Amazon EventBridge User Guide*.