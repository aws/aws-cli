**To create a metadata model for a SQL statement**

The following ``start-metadata-model-creation`` example queues the creation of a metadata model for a SQL statement. The selection rule specifies the schema where the metadata model is placed, and ``--metadata-model-name`` provides a unique identifier for use in subsequent operations. ::

    aws dms start-metadata-model-creation \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --selection-rules '{"rules": [{"rule-type": "selection", "rule-id": "1", "rule-name": "1", "object-locator": {"server-name": "example-source-server.us-east-1.rds.amazonaws.com", "database-name": "ExampleDatabase", "schema-name": "ExampleSchema"}, "rule-action": "explicit"}]}' \
        --metadata-model-name ExampleStatement \
        --properties StatementProperties={Definition="SELECT * FROM ExampleTable;"}

Output::

    {
        "RequestIdentifier": "a1b2c3d4-5678-90ab-cdef-EXAMPLE11111"
    }

For more information, see `Creating statement metadata models <https://docs.aws.amazon.com/dms/latest/userguide/sc-metadata-model.html#sc-metadata-model-creation>`__ in the *AWS Database Migration Service User Guide*.
