**To export converted metadata models to the target database**

The following ``start-metadata-model-export-to-target`` example queues an export of converted metadata models for all objects in the ``ExampleSchema`` schema to the target database. ::

    aws dms start-metadata-model-export-to-target \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --selection-rules '{"rules": [{"rule-type": "selection","rule-id": "1","rule-name": "1","object-locator": {"server-name": "example-target-server.us-east-1.rds.amazonaws.com", "schema-name": "ExampleSchema"},"rule-action": "explicit"}]}' \
        --overwrite-extension-pack

Output::

    {
        "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Applying your converted code <https://docs.aws.amazon.com/dms/latest/userguide/schema-conversion-save-apply.html#schema-conversion-apply>`__ in the *AWS Database Migration Service User Guide*.
