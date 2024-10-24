**To retrieve the discovered schema that was created by the Schemas service based on a sample event.**

The following ``get-discovered-schema`` retrieves the discovered schema that was created by the Schemas service based on a sample event. ::

	aws schemas get-discovered-schema \
		--events "{\"Source\":\"com.mycompany.myapp\",\"Detail\":\"{ \\\"key1\\\": \\\"value1\\\", \\\"key2\\\": \\\"value2\\\" }\",\"EventBusName\":\"default\",\"Resources\":[\"resource1\",\"resource2\"],\"DetailType\":\"myDetailType\"}" \
		--type OpenApi3

Output ::

	{
		"Content": "{\"openapi\":\"3.0.0\",\"info\":{\"version\":\"1.0.0\",\"title\":\"Event\"},\"paths\":{},\"components\":{\"schemas\":{\"Event\":{\"type\":\"object\",\"required\":[\"EventBusName\",\"DetailType\",\"Resources\",\"Detail\",\"Source\"],\"properties\":{\"Detail\":{\"type\":\"string\"},\"DetailType\":{\"type\":\"string\"},\"EventBusName\":{\"type\":\"string\"},\"Resources\":{\"type\":\"array\",\"items\":{\"type\":\"string\"}},\"Source\":{\"type\":\"string\"}}}}}}"
	}
	
For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.