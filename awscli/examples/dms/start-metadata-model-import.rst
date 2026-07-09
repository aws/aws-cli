**To import metadata from the source database**

The following ``start-metadata-model-import`` example queues a metadata import for all objects in the ``ExampleSchema`` schema from the source database. ::

    aws dms start-metadata-model-import \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --selection-rules '{"rules": [{"rule-type": "selection","rule-id": "1","rule-name": "1","object-locator": {"server-name": "example-source-server.us-east-1.rds.amazonaws.com", "schema-name": "ExampleSchema"},"rule-action": "explicit"}]}' \
        --origin SOURCE \
        --no-refresh

Output::

    {
        "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Navigating the metadata model tree <https://docs.aws.amazon.com/dms/latest/userguide/sc-metadata-model.html#sc-metadata-model-navigating>`__ in the *AWS Database Migration Service User Guide*.
