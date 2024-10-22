**To update the specified archive**

The following ``update-archive`` updates the specified archive. ::

	aws events update-archive \
		--archive-name hmhdmr --description "Prod archive"

Output ::

	{
		"ArchiveArn": "arn:aws:events:us-east-1:123456789101:archive/hmhdmr",
		"State": "ENABLED",
		"CreationTime": "2023-04-03T09:44:16+05:30"
	}

For more information, see `Archiving and replaying events in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/laProd/userguide/eb-archive.html>`__ in the *Amazon EventBridge User Guide*.