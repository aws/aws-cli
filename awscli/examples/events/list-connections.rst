**To retrieve a list of connections from the account**

The following ``list-connections`` retrieves a list of connections from the account. ::

	aws events list-connections

Output ::

	{
		"Connections": [
			{
				"ConnectionArn": "arn:aws:events:us-east-2:123456789101:connection/Api-Connection1/d29e45ad-137c-411f-9b78-221e4203f328",
				"Name": "Api-Connection1",
				"ConnectionState": "AUTHORIZED",
				"AuthorizationType": "BASIC",
				"CreationTime": "2023-03-29T10:26:11+00:00",
				"LastModifiedTime": "2023-03-29T10:26:11+00:00",
				"LastAuthorizedTime": "2023-03-29T10:26:11+00:00"
			},
			{
				"ConnectionArn": "arn:aws:events:us-east-2:123456789101:connection/con1/45f3f040-d1be-4d92-a49f-d3f7b30b5122",
				"Name": "con1",
				"ConnectionState": "AUTHORIZED",
				"AuthorizationType": "BASIC",
				"CreationTime": "2022-03-02T06:44:10+00:00",
				"LastModifiedTime": "2022-03-02T06:44:10+00:00",
				"LastAuthorizedTime": "2022-03-02T06:44:10+00:00"
			},
			{
				"ConnectionArn": "arn:aws:events:us-east-2:123456789101:connection/con2/6f39f463-2d10-48fc-b5b1-ff25a4bfd049",
				"Name": "con2",
				"ConnectionState": "AUTHORIZED",
				"AuthorizationType": "BASIC",
				"CreationTime": "2022-03-02T06:44:35+00:00",
				"LastModifiedTime": "2022-03-02T06:44:35+00:00",
				"LastAuthorizedTime": "2022-03-02T06:44:35+00:00"
			}
		]
	}

For more information, see `Connections for HTTP endpoint targets in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-target-connection.html>`__ in the *Amazon EventBridge User Guide*.