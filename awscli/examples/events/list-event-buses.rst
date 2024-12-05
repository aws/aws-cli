**To list all the event buses in your account**

The following ``list-event-buses`` lists all the event buses in your account, including the default event bus, custom event buses, and partner event buses. ::

	aws events list-event-buses

Output ::

	{
		"EventBuses": [
			{
				"Name": "default",
				"Arn": "arn:aws:events:us-east-1:123456789012:event-bus/default",
				"Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"allow_account_to_put_events\",\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"arn:aws:iam::012345678901:root\"},\"Action\":\"events:PutEvents\",\"Resource\":\"arn:aws:events:us-east-1:123456789012:event-bus/default\"}]}"
			},
			{
				"Name": "custom",
				"Arn": "arn:aws:events:us-east-1:123456789012:event-bus/custom",
				"Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"allow_account_to_put_events\",\"Effect\":\"Allow\",\"Principal\":{\"AWS\":[\"arn:aws:iam::012345678901:root\"},\"Action\":\"events:PutEvents\",\"Resource\":\"arn:aws:events:us-east-1:123456789012:event-bus/custom\"}]}"
			}
		]
	}
	
For more information, see `Event bus concepts in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is-how-it-works-concepts.html>`__ in the *Amazon EventBridge User Guide*.