**To create a connection**

The following ``create-connection`` creates a connection. A connection defines the authorization type and credentials to use for authorization with an API destination HTTP endpoint. ::

	aws events create-connection \
		--name ProdConnection \
		--authorization-type BASIC \
		--auth-parameters '{"BasicAuthParameters":{"Username":"string","Password":"string"}}'
 
Output ::

	{
		"ConnectionArn": "arn:aws:events:us-east-1:123456789012:connection/ProdConnection/53eb3384-f1c8-44b6-ba3a-66fe3cc5fd71",
		"ConnectionState": "AUTHORIZED",
		"CreationTime": "2024-04-20T07:21:19+00:00",
		"LastModifiedTime": "2024-04-20T07:21:19+00:00"
	}

For more information, see `Creating connections for HTTP endpoint targets in EventBridge <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-target-connection-create.html>`__ in the *Amazon EventBridge User Guide*.