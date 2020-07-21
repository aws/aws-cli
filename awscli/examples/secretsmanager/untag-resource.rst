**To remove tags from a secret**

The following example shows how to remove two tags from a secret's metadata. For each tag, both the key and its associated value are removed. ::

	aws secretsmanager untag-resource --secret-id MyTestDatabaseSecret \
	  --tag-keys '[ "FirstTag", "SecondTag"]'

There is no output from this API. To see the result, use the describe-secret operation.
