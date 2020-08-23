**To add tags to a secret**

The following example shows how to attach two tags each with a Key and Value to a secret. ::

	aws secretsmanager tag-resource --secret-id MyTestDatabaseSecret \
	  --tags '[{"Key": "FirstTag", "Value": "SomeValue"}, {"Key": "SecondTag", "Value": "AnotherValue"}]'

There is no output from this API. To see the result, use the describe-secret operation.
