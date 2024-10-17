**To export a schema to JSON format**

The following ``export-schemas`` exports a schema to JSON format. The command exports the latest schema version by default. Optionally, you may describe a specific schema version by using the --schema-version flag. Note: You may only export a schema in JSONSchemaDraft4 format. ::

	aws schemas export-schema \
		--registry-name aws.events \
		--schema-name aws.ec2@EC2InstanceStateChangeNotification \
		--type JSONSchemaDraft4 

Output::

	{
		"Content": "{\"$schema\":\"http://json-schema.org/draft-04/schema#\",\"title\":\"EC2InstanceStateChangeNotification\",\"definitions\":{\"EC2InstanceStateChangeNotification\":{\"properties\":{\"instance-id\":{\"type\":\"string\"},\"state\":{\"type\":\"string\"}},\"required\":[\"instance-id\",\"state\"],\"type\":\"object\"}},\"properties\":{\"account\":{\"type\":\"string\"},\"detail\":{\"$ref\":\"#/definitions/EC2InstanceStateChangeNotification\"},\"detail-type\":{\"type\":\"string\"},\"id\":{\"type\":\"string\"},\"region\":{\"type\":\"string\"},\"resources\":{\"items\":{\"type\":\"string\"},\"type\":\"array\"},\"source\":{\"type\":\"string\"},\"time\":{\"format\":\"date-time\",\"type\":\"string\"},\"version\":{\"type\":\"string\"}},\"required\":[\"detail-type\",\"resources\",\"id\",\"source\",\"time\",\"detail\",\"region\",\"version\",\"account\"],\"type\":\"object\",\"x-amazon-events-detail-type\":\"EC2 Instance State-change Notification\",\"x-amazon-events-source\":\"aws.ec2\"}",
		"SchemaName": "aws.ec2@EC2InstanceStateChangeNotification",
		"SchemaVersion": "1",
		"Type": "JSONSchemaDraft4"
	}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.