**To display details about an event bus in your account**

The following ``describe-event-bus`` displays details about an event bus in your account. ::

	aws events describe-event-bus --name "prodBus"

Output ::

	{
		"Name": "prodBus",
		"Arn": "arn:aws:events:us-east-1:123456789012:event-bus/prodBus",
		"Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"allow_account_to_put_events\",\"Effect\":\"Allow\",\"Principal\":{\"AWS\":[\"arn:aws:iam::123456789012:root\",\"arn:aws:iam::016284297628:root\"]},\"Action\":\"events:PutEvents\",\"Resource\":\"arn:aws:events:us-east-1:123456789012:event-bus/prodBus\"}]}"
	}

For more information, see `Event bus concepts in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-what-is-how-it-works-concepts.html>`__ in the *Amazon EventBridge User Guide*.