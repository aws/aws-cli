**To create an archive of events with the specified settings**

The following ``create-archive`` creates an archive of events with the specified settings. When you create an archive, incoming events might not immediately start being sent to the archive. Allow a short period of time for changes to take effect. If you do not specify a pattern to filter events sent to the archive, all events are sent to the archive except replayed event. ::

	aws events create-archive \
		--archive-name ProductionRuleArch \
		--event-source-arn "arn:aws:events:ca-central-1:123456789012:event-bus/test"

Output ::

	{
		"ArchiveArn": "arn:aws:events:ca-central-1:123456789012:archive/ProductionRuleArch",
		"State": "ENABLED",
		"CreationTime": "2024-10-21T15:10:56+00:00"
	}

For more information, see `Creating an archive for events in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-archive-event.html>`__ in the *Amazon EventBridge User Guide*.