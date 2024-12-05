**To retrieve a list of API destination in the account in the current Region**

The following ``list-api-destinations`` retrieves a list of API destination in the account in the current Region. ::

	aws events list-api-destinations

Output ::

	{
		"ApiDestinations": [
			{
				"ApiDestinationArn": "arn:aws:events:us-east-2:123456789101:api-destination/dest1/3435d8b6-a6ff-4096-8e32-27bc031d44ce",
				"Name": "dest1",
				"ApiDestinationState": "ACTIVE",
				"ConnectionArn": "arn:aws:events:us-east-2:123456789101:connection/con2/6f39f463-2d10-48fc-b5b1-ff25a4bfd049",
				"InvocationEndpoint": "https://example.com",
				"HttpMethod": "GET",
				"InvocationRateLimitPerSecond": 1,
				"CreationTime": "2022-03-02T06:44:35+00:00",
				"LastModifiedTime": "2022-03-02T06:44:35+00:00"
			},
			{
				"ApiDestinationArn": "arn:aws:events:us-east-2:123456789101:api-destination/new-api/ffd6b638-fc1b-4a84-8642-d5d45765b6f5",
				"Name": "new-api",
				"ApiDestinationState": "ACTIVE",
				"ConnectionArn": "arn:aws:events:us-east-2:123456789101:connection/Api-Connection1/d29e45ad-137c-411f-9b78-221e4203f328",
				"InvocationEndpoint": "https://google.com",
				"HttpMethod": "GET",
				"InvocationRateLimitPerSecond": 300,
				"CreationTime": "2023-03-29T10:26:12+00:00",
				"LastModifiedTime": "2023-03-29T10:26:12+00:00"
			}
		]
	}

For more information, see `API destinations as targets in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-api-destinations.html>`__ in the *Amazon EventBridge User Guide*.