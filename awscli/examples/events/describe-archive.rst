**To retrieve details about an archive**

The following ``describe-archive`` retrieves details about an archive. ::

	aws events describe-archive --archive-name "ProArchive"

Output ::

	{
		"ArchiveArn": "arn:aws:events:us-east-1:123456789012:archive/ProArchive",
		"ArchiveName": "ProArchive",
		"EventSourceArn": "arn:aws:events:us-east-1:123456789012:event-bus/default",
		"EventPattern": "{\"source\":[\"aws.ec2\"],\"detail-type\":[\"AWS API Call via CloudTrail\"],\"detail\":{\"eventSource\":[\"ec2.amazonaws.com\"]}}",
		"Description": "TestArchive",
		"State": "ENABLED",
		"RetentionDays": 0,
		"SizeBytes": 235439890,
		"EventCount": 115044,
		"CreationTime": "2023-04-03T03:38:02+00:00"
	}

For more information, see `Adding or removing archives on Amazon EventBridge event buses <https://docs.aws.amazon.com/eventbridge/latest/userguide/event-bus-update-archive.html>`__ in the *Amazon EventBridge User Guide*.