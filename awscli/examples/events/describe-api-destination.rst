**To retrieve details about an API destination**

The following ``describe-api-destination`` retrieves details about an API destination. ::

	aws events describe-api-destination --name "pro-api"

Output ::

	{
		"ApiDestinationArn": "arn:aws:events:us-east-1:123456789012:api-destination/pro-api/ffd6b638-fc1b-4a84-8642-d5d45765b6f5",
		"Name": "pro-api",
		"ApiDestinationState": "ACTIVE",
		"ConnectionArn": "arn:aws:events:us-east-1:123456789012:connection/Api-Connection1/d29e45ad-137c-411f-9b78-221e4203f328",
		"InvocationEndpoint": "https://google.com",
		"HttpMethod": "GET",
		"InvocationRateLimitPerSecond": 300,
		"CreationTime": "2023-03-29T10:26:12+00:00",
		"LastModifiedTime": "2023-03-29T10:26:12+00:00"
	}

For more information, see `API destinations as targets in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-api-destinations.html>`__ in the *Amazon EventBridge User Guide*.