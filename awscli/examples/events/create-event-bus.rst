**To create a new event bus within your account**

The following ``create-event-bus`` creates a new event bus within your account. This can be a custom event bus which you can use to receive events from your custom applications and services, or it can be a partner event bus which can be matched to a partner event source. ::

	aws events create-event-bus \
		--name prodbus

Output ::

	{
		"EventBusArn": "arn:aws:events:ca-central-1:123456789012:event-bus/prodbus"
	}

For more information, see `Creating an event bus in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-create-event-bus.html>`__ in the *Amazon EventBridge User Guide*.