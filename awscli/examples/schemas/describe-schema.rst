**To describe an existing schema definition in a registry**

The following ``describe-schema`` example describes an existing schema definition in a registry. The command describes the latest schema version by default. Optionally, you may describe a specific schema version by using the --schema-version flag. ::

    aws schemas describe-schema \
        --registry-name example-registry \
        --schema-name example-schema 

Output::

    {
        "Content": "{"Content":{"openapi":"3.0.0","info":{"version":"1.0.0","title":"Event"},"paths":{},"components":{"schemas":{"Event":{"type":"object","properties":{"ordinal":{"type":"number","format":"int64"},"name":{"type":"string"},"description":{"type":"string"},"price":{"type":"number","format":"double"},"address":{"type":"string"},"comments":{"type":"array","items":{"type":"string"}},"created_at":{"type":"string","format":"date-time"}}}}}},"LastModified":"2024-04-12T13:13:53+00:00","SchemaArn":"arn:aws:schemas:us-east-1:012345678912:schema/example-registry/example-schema","SchemaName":"example-schema","SchemaVersion":"3","Tags":{},"Type":"OpenApi3","VersionCreatedDate":"2024-04-12T13:13:53+00:00"}",
        "LastModified": "2024-04-12T13:13:53+00:00",
        "SchemaArn": "arn:aws:schemas:us-east-1:012345678912:schema/example-registry/example-schema",
        "SchemaName": "example-schema",
        "SchemaVersion": "3",
        "Tags": {},
        "Type": "OpenApi3",
        "VersionCreatedDate": "2024-04-12T13:13:53+00:00"
    }

For more information, see `Amazon EventBridge schemas <https://docs.aws.amazon.com/eventbridge/latest/userguide/eb-schema.html>`__ in the *Amazon EventBridge User Guide*.