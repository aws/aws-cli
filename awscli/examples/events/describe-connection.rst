**To retrieve details about a connection**

The following ``describe-connection`` retrieves details about a connection. ::

	aws events describe-connection --name "ProdConnection"

Output ::

	{
		"ConnectionArn": "arn:aws:events:us-east-1:123456789012:connection/ProdConnection/d29e45ad-137c-411f-9b78-221e4203f328",
		"Name": "ProdConnection1",
		"Description": "TestConnection",
		"ConnectionState": "AUTHORIZED",
		"AuthorizationType": "BASIC",
		"SecretArn": "arn:aws:secretsmanager:us-east-1:123456789012:secret:events!connection/ProdConnection1/2f54acf8-7d2b-4212-ace4-d73e82a3c005-owp1Jv",
		"AuthParameters": {
			"BasicAuthParameters": {
				"Username": "user"
			},
			"InvocationHttpParameters": {}
		},
		"CreationTime": "2023-03-29T10:26:11+00:00",
		"LastModifiedTime": "2023-03-29T10:26:11+00:00",
		"LastAuthorizedTime": "2023-03-29T10:26:11+00:00"
	}

For more information, see `Connections for HTTP endpoint targets in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-target-connection.html>`__ in the *Amazon EventBridge User Guide*.