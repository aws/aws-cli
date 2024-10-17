**To retrieve the resource-based policy associated with a particular registry**

The following ``get-resource-policy`` retrieves the resource-based policy associated with a particular registry. The command will only return a resource-policy if one exists on the registry. ::

	aws schemas get-resource-policy /
		--registry-name example-registry 

Output ::

	{
		"Policy": "{\"Version\":\"2012-10-17\",\"Statement\":[{\"Sid\":\"AllowReadWrite\",\"Effect\":\"Allow\",\"Principal\":{\"AWS\":\"*\"},\"Action\":\"schemas:*\",\"Resource\":[\"arn:aws:schemas:us-east-1:012345678912:registry/example-registry\",\"arn:aws:schemas:us-east-1:012345678912:schema/example-registry*\"]}]}",
		"RevisionId": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.