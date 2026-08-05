**To describe a metadata model**

The following ``describe-metadata-model`` example retrieves detailed information about the ``ExampleTable`` table in the ``ExampleSchema`` schema from the source metadata tree, including its SQL definition and references to the corresponding converted metadata models in the target database. ::

    aws dms describe-metadata-model \
        --migration-project-identifier arn:aws:dms:us-east-1:123456789012:migration-project:EXAMPLEABCDEFGHIJKLMNOPQRS \
        --selection-rules '{"rules": [{"rule-type": "selection", "rule-id": "1", "rule-name": "1", "object-locator": {"server-name": "example-source-server.us-east-1.rds.amazonaws.com", "schema-name": "ExampleSchema", "table-name": "ExampleTable"}, "rule-action": "explicit"}]}' \
        --origin SOURCE

Output::

    {
        "MetadataModelName": "ExampleTable",
        "MetadataModelType": "table",
        "TargetMetadataModels": [
            {
                "MetadataModelName": "exampletable",
                "SelectionRules": "{\"rules\": [{\"rule-type\": \"selection\", \"rule-id\": \"1\", \"rule-name\": \"1\", \"object-locator\": {\"server-name\": \"example-target-server.us-east-1.rds.amazonaws.com\", \"schema-name\": \"exampleschema\", \"table-name\": \"exampletable\"}, \"rule-action\": \"explicit\"}]}"
            }
        ],
        "Definition": "CREATE TABLE ExampleTable (ExampleColumn INTEGER NOT NULL);"
    }

For more information, see `Navigating the metadata model tree <https://docs.aws.amazon.com/dms/latest/userguide/sc-metadata-model.html#sc-metadata-model-navigating>`__ in the *AWS Database Migration Service User Guide*.
