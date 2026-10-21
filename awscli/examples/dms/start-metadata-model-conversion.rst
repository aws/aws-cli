**To convert all objects in a schema**

The following ``start-metadata-model-conversion`` example queues a conversion of all objects in the ``ExampleSchema`` schema to the target database format. ::

    aws dms start-metadata-model-conversion \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --selection-rules '{"rules": [{"rule-type": "selection","rule-id": "1","rule-name": "1","object-locator": {"server-name": "example-source-server.us-east-1.rds.amazonaws.com", "schema-name": "ExampleSchema"},"rule-action": "explicit"}]}'

Output::

    {
        "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Converting database schemas <https://docs.aws.amazon.com/dms/latest/userguide/schema-conversion-convert.html#schema-conversion-convert-steps>`__ in the *AWS Database Migration Service User Guide*.
