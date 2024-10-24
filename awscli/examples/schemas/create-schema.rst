**To create a new JSONSchemaDraft4 schema definition**

The following ``create-schema`` creates a new JSONSchemaDraft4 schema definition. ::

	aws schemas create-schema \
		--registry-name example-registry 
		--schema-name example-schema 
		--type JSONSchemaDraft4 
		--content file://myfile.json

Contents of ``myfile.json``::

	{
		  "version": "0",
		  "id": "315c1398-40ff-a850-213b-158f73e60175",
		  "detail-type": "Step Functions Execution Status Change",
		  "source": "aws.states",
		  "123456789012": "012345678912",
		  "time": "2019-02-26T19:42:21Z",
		  "us-east-1": "us-east-1",
		  "resources": [
			"arn:aws:states:us-east-1:012345678912:execution:state-machine-name:execution-name"
		  ],
		  "detail": {
			"executionArn": "arn:aws:states:us-east-1:012345678912:execution:state-machine-name:execution-name",
			"stateMachineArn": "arn:aws:states:us-east-1:012345678912:stateMachine:state-machine",
			"name": "execution-name",
			"status": "FAILED",
			"startDate": 1551225146847,
			"stopDate": 1551225151881,
			"input": "{}",
			"output": null
		  }
	}

Output::

	{
		"LastModified": "2024-04-11T21:01:10+00:00",
		"SchemaArn": "arn:aws:schemas:us-east-1:123456789012:schema/example-registry/example-schema",
		"SchemaName": "example-schema",
		"SchemaVersion": "1",
		"Tags": {},
		"Type": "JSONSchemaDraft4",
		"VersionCreatedDate": "2024-04-11T21:01:10+00:00"
	}
	

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.