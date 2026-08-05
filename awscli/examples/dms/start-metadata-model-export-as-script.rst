**To export converted metadata models as DDL scripts**

The following ``start-metadata-model-export-as-script`` example queues an export of converted metadata models for all objects in the ``ExampleSchema`` schema as data definition language (DDL) scripts to the Amazon S3 bucket associated with the migration project. ::

    aws dms start-metadata-model-export-as-script \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --selection-rules '{"rules": [{"rule-type": "selection","rule-id": "1","rule-name": "1","object-locator": {"server-name": "example-target-server.us-east-1.rds.amazonaws.com", "schema-name": "ExampleSchema"},"rule-action": "explicit"}]}' \
        --origin TARGET \
        --file-name ExampleScript

Output::

    {
        "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Saving your converted code to a SQL file <https://docs.aws.amazon.com/dms/latest/userguide/schema-conversion-save-apply.html#schema-conversion-save>`__ in the *AWS Database Migration Service User Guide*.
