**To get the information about an existing global endpoint**

The following ``describe-endpoint`` will get the information about an existing global endpoint. ::

	aws events describe-endpoint --name prod

Output ::

	{
		"Name": "prod",
		"Description": "sample endpoint",
		"Arn": "arn:aws:events:us-east-1:123456789101:endpoint/prod",
		"RoutingConfig": {
			"FailoverConfig": {
				"Primary": {
					"HealthCheck": "arn:aws:route53:::healthcheck/8f7dc0b8-ad9e-1234-846e-3a475c53bb76"
				},
				"Secondary": {
					"Route": "us-east-2"
				}
			}
		},
		"ReplicationConfig": {
			"State": "ENABLED"
		},
		"EventBuses": [
			{
				"EventBusArn": "arn:aws:events:us-east-1:123456789101:event-bus/prod"
			},
			{
				"EventBusArn": "arn:aws:events:us-east-2:123456789101:event-bus/prod"
			}
		],
		"RoleArn": "arn:aws:iam::123456789101:role/service-role/Amazon_EventBridge_Invoke_Event_Bus_prod",
		"EndpointId": "prod.veo",
		"EndpointUrl": "https://prod.veo.endpoint.events.amazonaws.com",
		"State": "ACTIVE",
		"CreationTime": "2024-05-19T15:22:58.463000+05:30",
		"LastModifiedTime": "2024-05-19T15:23:00.311000+05:30"
	}

For more information, see `Global endpoint in Amazon EventBridge <https://docs.aws.amazon.com/eventbridge/laprod/userguide/eb-ge-create-endpoint.html>`__ in the *Amazon EventBridge User Guide*.