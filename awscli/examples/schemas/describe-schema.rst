**To describe an existing schema definition in a registry**

The following ``describe-schema`` describes an existing schema definition in a registry. The command describes the latest schema version by default. Optionally, you may describe a specific schema version by using the --schema-version flag. ::

	aws schemas describe-schema \
		--registry-name example-registry \
		--schema-name example-schema 

Output::

{
    "Content": "{\n  \"openapi\": \"3.0.0\",\n  \"info\": {\n    \"version\": \"1.0.0\",\n    \"title\": \"Event\"\n  },\n  \"paths\": {},\n  \"components\": {\n    \"schemas\": {\n      \"Event\": {\n        \"type\": \"object\",\n        \"properties\": {\n          \"ordinal\": {\n            \"type\": \"number\",\n            \"format\": \"int64\"\n          },\n          \"name\": {\n            \"type\": \"string\"\n          },\n          \"description\": {\n            \"type\": \"string\"\n          },\n          \"price\": {\n            \"type\": \"number\",\n            \"format\": \"double\"\n          },\n          \"address\": {\n            \"type\": \"string\"\n          },\n          \"comments\": {\n            \"type\": \"array\",\n            \"items\": {\n              \"type\": \"string\"\n            }\n          },\n          \"created_at\": {\n            \"type\": \"string\",\n            \"format\": \"date-time\"\n          }\n        }\n      }\n    }\n  }\n}",
    "LastModified": "2024-04-12T13:13:53+00:00",
    "SchemaArn": "arn:aws:schemas:us-east-1:012345678912:schema/example-registry/example-schema",
    "SchemaName": "example-schema",
    "SchemaVersion": "3",
    "Tags": {},
    "Type": "OpenApi3",
    "VersionCreatedDate": "2024-04-12T13:13:53+00:00"
}

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.